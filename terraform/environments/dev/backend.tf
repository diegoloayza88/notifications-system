terraform {
  cloud {
    organization = "portfolio-diego"

    workspaces {
      name = "notifications-system-dev"
    }
  }
}
