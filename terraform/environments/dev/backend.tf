terraform {
  cloud {
    organization = "TU_ORGANIZACION"  # ← CAMBIAR ESTO

    workspaces {
      name = "event-notifications-dev"
    }
  }
}
