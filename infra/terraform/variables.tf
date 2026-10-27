variable "container_port" {
  description = "Port exposed by the FastAPI application inside the container."
  type        = number
  default     = 8000
}

variable "host_port" {
  description = "Host port for the API."
  type        = number
  default     = 8001
}
