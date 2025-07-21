using System.Net;
using System.Net.Http.Json;
using Microsoft.AspNetCore.Mvc.Testing;

namespace MusicRecommendationService.Tests;

public class RecommendationEndpointTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient _client;

    public RecommendationEndpointTests(WebApplicationFactory<Program> factory)
    {
        _client = factory.CreateClient();
    }

    [Fact]
    public async Task GetRecommendations_ReturnsOk_ForExistingTrack()
    {
        // Act
        var response = await _client.GetAsync("/recommendations/101");

        // Assert
        response.EnsureSuccessStatusCode();
        var recommendations = await response.Content.ReadFromJsonAsync<List<int>>();
        Assert.NotNull(recommendations);
        Assert.Equal(new List<int> { 102, 105 }, recommendations);
    }

    [Fact]
    public async Task GetRecommendations_ReturnsNotFound_ForNonExistingTrack()
    {
        // Act
        var response = await _client.GetAsync("/recommendations/999");

        // Assert
        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }
}
