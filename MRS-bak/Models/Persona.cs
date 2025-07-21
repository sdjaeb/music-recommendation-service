namespace MusicRecommendationService.Models;

public class Persona
{
  public int UserId { get; set; }
  public List<int> LikedTracks { get; set; } = new();
}