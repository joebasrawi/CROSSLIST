import XCTest
@testable import CROSSLISTCore

final class SpotifyPlaylistLinkTests: XCTestCase {
    func testParsesSpotifyURL() {
        XCTAssertEqual(
            SpotifyPlaylistLink.playlistID(
                from: "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=test"
            ),
            "37i9dQZF1DXcBWIGoYBM5M"
        )
    }

    func testParsesLocalizedSpotifyURL() {
        XCTAssertEqual(
            SpotifyPlaylistLink.playlistID(
                from: "https://open.spotify.com/intl-fr/playlist/37i9dQZF1DXcBWIGoYBM5M"
            ),
            "37i9dQZF1DXcBWIGoYBM5M"
        )
    }

    func testRejectsTrackURL() {
        XCTAssertNil(
            SpotifyPlaylistLink.playlistID(
                from: "https://open.spotify.com/track/37i9dQZF1DXcBWIGoYBM5M"
            )
        )
    }
}
