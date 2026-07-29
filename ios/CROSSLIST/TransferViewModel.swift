import Foundation

@MainActor
final class TransferViewModel: ObservableObject {
    enum Phase: Equatable {
        case idle
        case loading
        case ready
        case creating
        case success
        case failure(String)
    }

    @Published var playlistURL = ""
    @Published private(set) var phase: Phase = .idle
    @Published private(set) var preview: TransferPreview?

    private let apiClient: APIClient?
    private let musicService: AppleMusicPlaylistService

    init(apiClient: APIClient? = try? APIClient(), musicService: AppleMusicPlaylistService = .init()) {
        self.apiClient = apiClient
        self.musicService = musicService
    }

    var canPreview: Bool {
        SpotifyPlaylistLink.isValid(playlistURL) && phase != .loading && phase != .creating
    }

    var isBusy: Bool {
        phase == .loading || phase == .creating
    }

    func loadPreview() async {
        guard let apiClient else {
            phase = .failure("CROSSLIST needs a valid API server URL in its app configuration.")
            return
        }
        guard SpotifyPlaylistLink.isValid(playlistURL) else {
            phase = .failure("Paste a valid Spotify playlist link.")
            return
        }

        phase = .loading
        preview = nil
        do {
            let storefront = Locale.current.region?.identifier.lowercased() ?? "us"
            preview = try await apiClient.preview(
                playlistURL: playlistURL,
                storefront: storefront
            )
            phase = .ready
        } catch {
            phase = .failure(error.localizedDescription)
        }
    }

    func createPlaylist() async -> URL? {
        guard let preview else { return nil }
        phase = .creating
        do {
            let url = try await musicService.createPlaylist(from: preview)
            phase = .success
            return url
        } catch {
            phase = .failure(error.localizedDescription)
            return nil
        }
    }

    func acceptIncomingURL(_ url: URL) {
        guard url.scheme == "crosslist",
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let value = components.queryItems?.first(where: { $0.name == "url" })?.value else {
            return
        }
        playlistURL = value
        Task { await loadPreview() }
    }

    func reset() {
        playlistURL = ""
        preview = nil
        phase = .idle
    }
}
