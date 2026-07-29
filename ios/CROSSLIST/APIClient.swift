import Foundation

enum CROSSLISTAPIError: LocalizedError {
    case invalidBaseURL
    case invalidResponse
    case service(message: String, hint: String?)

    var errorDescription: String? {
        switch self {
        case .invalidBaseURL:
            return "CROSSLIST is missing its server address."
        case .invalidResponse:
            return "CROSSLIST received an unexpected response."
        case let .service(message, hint):
            return [message, hint].compactMap { $0 }.joined(separator: "\n\n")
        }
    }
}

struct APIClient: Sendable {
    private let session: URLSession
    private let baseURL: URL

    init(session: URLSession = .shared, baseURL: URL? = nil) throws {
        let configured = Bundle.main.object(forInfoDictionaryKey: "CROSSLIST_API_BASE_URL") as? String
        guard let resolved = baseURL ?? configured.flatMap(URL.init(string:)) else {
            throw CROSSLISTAPIError.invalidBaseURL
        }
        self.session = session
        self.baseURL = resolved
    }

    func preview(playlistURL: String, storefront: String) async throws -> TransferPreview {
        let endpoint = baseURL.appendingPathComponent("v1/transfers/spotify-to-apple/preview")
        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(
            PreviewRequest(playlistURL: playlistURL, storefront: storefront)
        )

        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw CROSSLISTAPIError.invalidResponse
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        guard (200..<300).contains(httpResponse.statusCode) else {
            if let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data) {
                throw CROSSLISTAPIError.service(
                    message: envelope.error.message,
                    hint: envelope.error.hint
                )
            }
            throw CROSSLISTAPIError.invalidResponse
        }
        return try decoder.decode(TransferPreview.self, from: data)
    }
}
