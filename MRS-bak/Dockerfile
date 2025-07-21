# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["MusicRecommendationService.csproj", "./"]
RUN dotnet restore "MusicRecommendationService.csproj"
COPY . ./
RUN dotnet publish "MusicRecommendationService.csproj" -c Release

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:7.0 AS runtime
WORKDIR /app
COPY --from=build /app/publish ./
EXPOSE 80
ENTRYPOINT ["dotnet", "MusicRecService.dll"]
