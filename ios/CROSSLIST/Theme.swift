import SwiftUI

enum CROSSLISTTheme {
    static let background = Color(red: 0.035, green: 0.035, blue: 0.04)
    static let surface = Color.white.opacity(0.075)
    static let surfaceStrong = Color.white.opacity(0.12)
    static let accent = Color(red: 0.78, green: 1.0, blue: 0.18)
    static let muted = Color.white.opacity(0.62)
}

struct CROSSLISTButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(.black)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(CROSSLISTTheme.accent.opacity(configuration.isPressed ? 0.72 : 1))
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .scaleEffect(configuration.isPressed ? 0.985 : 1)
            .animation(.easeOut(duration: 0.14), value: configuration.isPressed)
    }
}
