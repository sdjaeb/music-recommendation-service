#!/bin/bash

# This script recreates the directory structure and files for the harmanpoc project.
# Note: The base path is hardcoded to /Users/sdjaeb/dev/. You may need to adjust this.

# --- Create the base directory structure ---
echo "Creating directory structure..."
mkdir -p /Users/sdjaeb/dev/harmanpoc/MusicRecommendationService/Data
mkdir -p /Users/sdjaeb/dev/harmanpoc/MusicRecommendationService/Models
mkdir -p /Users/sdjaeb/dev/harmanpoc/MusicRecommendationService/Properties
mkdir -p /Users/sdjaeb/dev/harmanpoc/MusicRecommendationService/Services
mkdir -p /Users/sdjaeb/dev/harmanpoc/MusicRecommendationService.Tests
mkdir -p /Users/sdjaeb/dev/harmanpoc/.github/workflows

# --- Create project files ---
echo "Creating project files..."

# Solution File
cat <<'EOF' > /Users/sdjaeb/dev/harmanpoc/harmanpoc.sln
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.5.2.0
MinimumVisualStudioVersion = 10.0.40219.1
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "MusicRecommendationService", "MusicRecommendationService\MusicRecommendationService.csproj", "{A5E67D81-6CC7-85B6-05A9-AAB91725B563}"
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{A5E67D81-6CC7-85B6-05A9-AAB91725B563}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{A5E67D81-6CC7-85B6-05A9-AAB91725B563}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{A5E67D81-6CC7-85B6-05A9-AAB91725B563}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{A5E67D81-6CC7-85B6-05A9-AAB91725B563}.Release|Any CPU.Build.0 = Release|Any CPU
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {FA8BEF77-F348-4F63-A023-A8785B564F06}
	EndGlobalSection
EndGlobal
EOF
