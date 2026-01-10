import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
import boto3
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger()


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API."""

    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self):
        """Initialize the Google Sheets client."""
        self.secrets_client = boto3.client('secretsmanager')
        self.credentials = self._get_credentials()
        self.service = build('sheets', 'v4', credentials=self.credentials)

    def _get_credentials(self) -> service_account.Credentials:
        """
        Retrieve Google service account credentials from Secrets Manager.

        Returns:
            Google service account credentials
        """
        try:
            secret_arn = os.environ['GOOGLE_CREDENTIALS']
            response = self.secrets_client.get_secret_value(SecretId=secret_arn)
            credentials_json = json.loads(response['SecretString'])

            return service_account.Credentials.from_service_account_info(
                credentials_json,
                scopes=self.SCOPES
            )
        except Exception as e:
            logger.error(f"Error retrieving Google credentials: {str(e)}")
            raise

    def read_sheet(
            self,
            spreadsheet_id: str,
            range_name: str
    ) -> List[List[Any]]:
        """
        Read data from a Google Sheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The A1 notation of the range to retrieve

        Returns:
            List of rows from the sheet
        """
        try:
            logger.info(f"Reading sheet: {spreadsheet_id}, range: {range_name}")

            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            logger.info(f"Retrieved {len(values)} rows from sheet")

            return values

        except HttpError as error:
            logger.error(f"Google Sheets API error: {error}")
            raise
        except Exception as e:
            logger.error(f"Error reading sheet: {str(e)}")
            raise

    def get_sheet_metadata(
            self,
            spreadsheet_id: str
    ) -> Dict[str, Any]:
        """
        Get metadata about a spreadsheet.

        Args:
            spreadsheet_id: The ID of the spreadsheet

        Returns:
            Spreadsheet metadata
        """
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()

            return result

        except HttpError as error:
            logger.error(f"Google Sheets API error: {error}")
            raise

    def calculate_sheet_hash(
            self,
            spreadsheet_id: str,
            range_name: str
    ) -> str:
        """
        Calculate a hash of the sheet content to detect changes.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            range_name: The range to hash

        Returns:
            SHA256 hash of the content
        """
        try:
            values = self.read_sheet(spreadsheet_id, range_name)
            content = json.dumps(values, sort_keys=True)
            return hashlib.sha256(content.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating sheet hash: {str(e)}")
            raise

    def batch_read_sheets(
            self,
            spreadsheet_id: str,
            ranges: List[str]
    ) -> Dict[str, List[List[Any]]]:
        """
        Read multiple ranges from a sheet in a single API call.

        Args:
            spreadsheet_id: The ID of the spreadsheet
            ranges: List of A1 notation ranges

        Returns:
            Dictionary mapping range names to their values
        """
        try:
            logger.info(f"Batch reading {len(ranges)} ranges from {spreadsheet_id}")

            result = self.service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id,
                ranges=ranges
            ).execute()

            value_ranges = result.get('valueRanges', [])

            return {
                vr['range']: vr.get('values', [])
                for vr in value_ranges
            }

        except HttpError as error:
            logger.error(f"Google Sheets API error: {error}")
            raise