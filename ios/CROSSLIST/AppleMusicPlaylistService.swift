import Foundation
import MusicKit

enum AppleMusicPlaylistError: LocalizedError {
    case permissionDenied
    case noMatchedTracks
    case songsUnavailable

    var errorDescription: String? {
        switch self {
        case .permissionDenied:
            return "Allow Apple Music access to create the playlist. You can change this in Settings."
        case .noMatchedTracks:
            return "There are no matched Apple Music songs to add."
        case .songsUnavailable:
            return "The matched songs are not available in your Apple Music storefront."
        }
    }
}

struct AppleMusicPlaylistService {
    func createPlaylist(from preview: TransferPreview) async throws -> URL? {
        let authorization = await MusicAuthorization.request()
        guard authorization == .authorized else {
            throw AppleMusicPlaylistError.permissionDenied
        }

        let orderedIDs = preview.tracks.compactMap { track in
            track.match.map { MusicItemID($0.id) }
        }
        guard !orderedIDs.isEmpty else {
            throw AppleMusicPlaylistError.noMatchedTracks
        }

        var songsByID: [MusicItemID: Song] = [:]
        for batch in orderedIDs.chunked(into: 25) {
            var request = MusicCatalogResourceRequest<Song>(matching: \.id, memberOf: batch)
            request.limit = batch.count
            let response = try await request.response()
            for song in response.items {
                songsByID[song.id] = song
            }
        }

        let orderedSongs = orderedIDs.compactMap { songsByID[$0] }
        guard !orderedSongs.isEmpty else {
            throw AppleMusicPlaylistError.songsUnavailable
        }

        let description = "Transferred from Spotify with CROSSLIST. \(preview.matchedCount) songs matched."
        let playlist = try await MusicLibrary.shared.createPlaylist(
            name: preview.playlist.name,
            description: description,
            authorDisplayName: "CROSSLIST",
            items: orderedSongs
        )
        return playlist.url
    }
}

private extension Array {
    func chunked(into size: Int) -> [[Element]] {
        guard size > 0 else { return [] }
        return stride(from: 0, to: count, by: size).map {
            Array(self[$0..<Swift.min($0 + size, count)])
        }
    }
}
