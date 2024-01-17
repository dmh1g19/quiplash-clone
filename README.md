# Quiplash Clone - Interactive Multiplayer Game Platform

## Overview
This repository hosts a Quiplash clone, an interactive multiplayer game for 3-8 players with additional audience participation. The game, built with VueJS, NodeJS, and socket.io on the frontend and Python with Azure on the backend, offers a dynamic and engaging experience similar to the popular party game Quiplash.

## Features
- **Player Capacity:** 3-8 players, with additional audience participation.
- **Rounds:** Three rounds of increasing excitement and point values.
- **Prompt Collection:** Players and audience submit prompts, reused in the game and stored for future sessions.
- **Answer Submission:** Players respond to prompts aiming for humor and wit.
- **Voting System:** All players and audience vote on answers, except for their own submissions.
- **Scoreboard:** Real-time tracking of scores and leaderboard.

## Technical Specifications
- **Frontend:** VueJS and JavaScript for responsive player interaction.
- **Backend:** Python with Azure functions for efficient serverless operations.
- **Communication:** Real-time updates via NodeJS and socket.io.
- **Cloud Deployment:** Tailored for deployment on Google App Engine.

## Cloud Integration
- Backend leveraging Azure functions for high scalability and performance.
- Frontend seamlessly deployed on Google App Engine for robust accessibility.

## Getting Started
1. Clone the repository.
2. Install dependencies: `npm install`.
3. Run locally: `npm start`.
4. Deploy to Google App Engine: `npm gdeploy`.

## Contribution
Your contributions are welcome. Feel free to fork, submit pull requests, or report issues.
