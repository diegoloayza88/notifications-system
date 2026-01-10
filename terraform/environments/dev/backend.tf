terraform {
  cloud {
    organization = "portfolio-diego"

    workspaces {
      name = "event-notifications-dev"
    }
  }
}
