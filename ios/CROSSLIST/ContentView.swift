import SwiftUI
import UniformTypeIdentifiers

struct ContentView: View {
    @StateObject private var model = TransferViewModel()
    @Environment(\.openURL) private var openURL

    var body: some View {
        ZStack {
            CROSSLISTTheme.background.ignoresSafeArea()
            LinearGradient(
                colors: [CROSSLISTTheme.accent.opacity(0.16), .clear, .purple.opacity(0.09)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    brand
                    hero
                    inputCard

                    if let preview = model.preview {
                        previewCard(preview)
                    }

                    if case let .failure(message) = model.phase {
                        errorCard(message)
                    }

                    privacyNote
                }
                .padding(.horizontal, 22)
                .padding(.top, 22)
                .padding(.bottom, 44)
            }
        }
        .preferredColorScheme(.dark)
        .onOpenURL(perform: model.acceptIncomingURL)
    }

    private var brand: some View {
        HStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 11, style: .continuous)
                    .fill(CROSSLISTTheme.accent)
                    .frame(width: 38, height: 38)
                Image(systemName: "arrow.left.arrow.right")
                    .font(.system(size: 17, weight: .black))
                    .foregroundStyle(.black)
            }
            Text("CROSSLIST")
                .font(.system(size: 18, weight: .black, design: .rounded))
                .tracking(1.4)
            Spacer()
            Text("SPOTIFY →  MUSIC")
                .font(.caption2.weight(.bold))
                .foregroundStyle(CROSSLISTTheme.muted)
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("One link.\nSame playlist.")
                .font(.system(size: 48, weight: .black, design: .rounded))
                .tracking(-1.8)
                .minimumScaleFactor(0.8)
            Text("Paste a public Spotify playlist. CROSSLIST matches it and adds it straight to Apple Music.")
                .font(.title3)
                .foregroundStyle(CROSSLISTTheme.muted)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var inputCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("SPOTIFY PLAYLIST LINK")
                .font(.caption.weight(.bold))
                .tracking(1.2)
                .foregroundStyle(CROSSLISTTheme.muted)

            HStack(spacing: 10) {
                Image(systemName: "link")
                    .foregroundStyle(CROSSLISTTheme.accent)
                TextField("open.spotify.com/playlist/…", text: $model.playlistURL)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .submitLabel(.go)
                    .onSubmit {
                        guard model.canPreview else { return }
                        Task { await model.loadPreview() }
                    }
                PasteButton(payloadType: String.self) { strings in
                    if let link = strings.first {
                        model.playlistURL = link
                    }
                }
                .labelStyle(.iconOnly)
                .tint(CROSSLISTTheme.accent)
            }
            .padding(14)
            .background(Color.black.opacity(0.28))
            .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
            }

            Button {
                Task { await model.loadPreview() }
            } label: {
                HStack {
                    if model.phase == .loading {
                        ProgressView().tint(.black)
                    } else {
                        Image(systemName: "magnifyingglass")
                    }
                    Text(model.phase == .loading ? "Matching tracks…" : "Find this playlist")
                }
            }
            .buttonStyle(CROSSLISTButtonStyle())
            .disabled(!model.canPreview)
            .opacity(model.canPreview ? 1 : 0.45)
        }
        .padding(18)
        .background(CROSSLISTTheme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        }
    }

    private func previewCard(_ preview: TransferPreview) -> some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(spacing: 14) {
                AsyncImage(url: preview.playlist.artworkURL) { image in
                    image.resizable().scaledToFill()
                } placeholder: {
                    ZStack {
                        CROSSLISTTheme.surfaceStrong
                        Image(systemName: "music.note.list")
                            .foregroundStyle(CROSSLISTTheme.muted)
                    }
                }
                .frame(width: 76, height: 76)
                .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))

                VStack(alignment: .leading, spacing: 5) {
                    Text(preview.playlist.name)
                        .font(.title3.bold())
                        .lineLimit(2)
                    Text("\(preview.matchedCount) of \(preview.tracks.count) songs matched")
                        .font(.subheadline)
                        .foregroundStyle(CROSSLISTTheme.muted)
                }
                Spacer()
            }

            if preview.unmatchedCount > 0 {
                Label(
                    "\(preview.unmatchedCount) unavailable \(preview.unmatchedCount == 1 ? "song" : "songs") will be skipped.",
                    systemImage: "exclamationmark.circle"
                )
                .font(.footnote)
                .foregroundStyle(.orange)
            }

            Button {
                Task {
                    if let url = await model.createPlaylist() {
                        openURL(url)
                    }
                }
            } label: {
                HStack {
                    if model.phase == .creating {
                        ProgressView().tint(.black)
                    } else if model.phase == .success {
                        Image(systemName: "checkmark.circle.fill")
                    } else {
                        Image(systemName: "apple.logo")
                    }
                    Text(createButtonTitle(preview))
                }
            }
            .buttonStyle(CROSSLISTButtonStyle())
            .disabled(model.isBusy || preview.matchedCount == 0 || model.phase == .success)
        }
        .padding(18)
        .background(CROSSLISTTheme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        }
    }

    private func createButtonTitle(_ preview: TransferPreview) -> String {
        switch model.phase {
        case .creating:
            return "Adding to Apple Music…"
        case .success:
            return "Added to Apple Music"
        default:
            return "Add \(preview.matchedCount) songs to Apple Music"
        }
    }

    private func errorCard(_ message: String) -> some View {
        Label {
            Text(message)
                .font(.subheadline)
                .fixedSize(horizontal: false, vertical: true)
        } icon: {
            Image(systemName: "exclamationmark.triangle.fill")
        }
        .foregroundStyle(.orange)
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.orange.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var privacyNote: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "lock.shield")
                .foregroundStyle(CROSSLISTTheme.accent)
            Text("No Apple password. iOS asks for Music access once, then CROSSLIST creates playlists locally on your device.")
                .font(.footnote)
                .foregroundStyle(CROSSLISTTheme.muted)
        }
    }
}

#Preview {
    ContentView()
}
