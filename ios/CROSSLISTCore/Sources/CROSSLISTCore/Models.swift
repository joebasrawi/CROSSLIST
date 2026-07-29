import Foundation

public struct PreviewRequest: Encodable, Sendable {
    public let playlistURL: String
    public let storefront: String

    public init(playlistURL: String, storefront: String) {
        self.playlistURL = playlistURL
        self.storefront = storefront
    }
}

public struct SourceTrack: Codable, Identifiable, Sendable {
    public var id: String { "\(position)-\(spotifyID)" }
    public let position: Int
    public let spotifyID: String
    public let name: String
    public let artist: String
    public let album: String?
    public let durationMs: Int?
    public let isrc: String?
    public let artworkURL: URL?
}

public struct AppleMusicMatch: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let artist: String
    public let album: String?
    public let durationMs: Int?
    public let url: URL?
    public let artworkURL: URL?
    public let confidence: Double
    public let method: String
}

public struct PreviewTrack: Codable, Identifiable, Sendable {
    public var id: String { source.id }
    public let source: SourceTrack
    public let status: String
    public let match: AppleMusicMatch?
}

public struct PlaylistSummary: Codable, Sendable {
    public let spotifyID: String
    public let name: String
    public let description: String?
    public let sourceURL: URL
    public let artworkURL: URL?
    public let totalTracks: Int
}

public struct TransferPreview: Codable, Sendable {
    public let playlist: PlaylistSummary
    public let tracks: [PreviewTrack]
    public let matchedCount: Int
    public let unmatchedCount: Int
    public let storefront: String
}

public struct APIErrorEnvelope: Decodable, Sendable {
    public struct APIError: Decodable, Sendable {
        public let code: String
        public let message: String
        public let hint: String?
    }

    public let error: APIError
}

public enum SpotifyPlaylistLink {
    public static func isValid(_ value: String) -> Bool {
        playlistID(from: value) != nil
    }

    public static func playlistID(from value: String) -> String? {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let candidate: String?

        if trimmed.hasPrefix("spotify:playlist:") {
            candidate = String(trimmed.dropFirst("spotify:playlist:".count))
                .split(separator: "?")
                .first
                .map(String.init)
        } else if let url = URL(string: trimmed),
                  ["open.spotify.com", "www.open.spotify.com"].contains(url.host?.lowercased() ?? "") {
            let segments = url.pathComponents.filter { $0 != "/" }
            guard let index = segments.firstIndex(of: "playlist"), segments.indices.contains(index + 1) else {
                return nil
            }
            candidate = segments[index + 1]
        } else {
            candidate = nil
        }

        guard let candidate, candidate.count == 22,
              candidate.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber) }) else {
            return nil
        }
        return candidate
    }
}
