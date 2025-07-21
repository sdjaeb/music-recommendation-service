# Build stage
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["MusicRecommendationService.csproj", "./"]
RUN dotnet restore "MusicRecommendationService.csproj"
COPY . .
RUN dotnet publish "MusicRecommendationService.csproj" -c Release -o /app/publish

# Runtime stage
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /app/publish .
ENV ASPNETCORE_URLS=http://+:80
EXPOSE 80
ENTRYPOINT ["dotnet", "MusicRecommendationService.dll"]
