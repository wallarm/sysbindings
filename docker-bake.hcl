target "default" {
    dockerfile = "./Dockerfile"
    context = "."
    pull = true
    no-cache = true
    output = [
        "type=registry",
    ]
    platforms = [
        "linux/amd64",
        "linux/386",
        "linux/arm64",
        "linux/arm/v7",
        "linux/arm/v6",
    ]
}
