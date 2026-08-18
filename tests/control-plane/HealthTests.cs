using System.Net;
using Microsoft.AspNetCore.Mvc.Testing;
using Xunit;

namespace ControlPlane.Tests;

public sealed class HealthTests : IClassFixture<WebApplicationFactory<Program>>
{
    private readonly HttpClient client;

    public HealthTests(WebApplicationFactory<Program> factory)
    {
        client = factory.CreateClient();
    }

    [Fact]
    public async Task Health_returns_success()
    {
        using var response = await client.GetAsync("/health");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
    }
}
