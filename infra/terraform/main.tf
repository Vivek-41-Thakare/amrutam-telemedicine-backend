terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_image" "api" {
  name = "amrutam-telemedicine-api:latest"
  build {
    context = "../.."
  }
}

resource "docker_container" "api" {
  name  = "amrutam-telemedicine-api"
  image = docker_image.api.image_id

  ports {
    internal = var.container_port
    external = var.host_port
  }

  restart = "unless-stopped"
}
