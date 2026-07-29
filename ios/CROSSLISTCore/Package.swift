// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "CROSSLISTCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v13),
    ],
    products: [
        .library(name: "CROSSLISTCore", targets: ["CROSSLISTCore"]),
    ],
    targets: [
        .target(name: "CROSSLISTCore"),
        .testTarget(name: "CROSSLISTCoreTests", dependencies: ["CROSSLISTCore"]),
    ]
)

