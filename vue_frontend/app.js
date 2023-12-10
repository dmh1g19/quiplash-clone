'use strict';


const request = require('request')
const dotenv = require('dotenv');
dotenv.config();

//The game state
const PLAYERS_MAX = 8
let nextClientId = 0;
let players = new Map();
let nonPlayer = new Map();
let apiPrompts = [];
let localPrompts = [];
let displays = [];
let activePrompts = new Map();
let state = {stage: 1, round: 1};
let clientList = {socketToClient: new Map(), clientToSocket: new Map()};
let currentPromptIndex = 0;
let singlePrompts = new Map();
let numOfVotes = 0;
let initialPrompt = true;

//Set up azure function interface
const fetch = require('node-fetch');
const baseURL = process.env.BASE_URL;
const accessCode = process.env.ACCESS_CODE;
const PORT = process.env.PORT;

//Set up express
const express = require('express');
const { exit } = require('process');
const app = express();

//Setup socket.io
const server = require('http').Server(app);
const io = require('socket.io')(server);

//Setup static page handling
app.set('view engine', 'ejs');
app.use('/static', express.static('public'));

//Handle client interface on /
app.get('/', (req, res) => {
  res.render('client');
});
//Handle display interface on /display
app.get('/display', (req, res) => {
  res.render('display');
});

//Start the server
function startServer() {
    server.listen(PORT, () => {
        console.log(`Server listening on port ${PORT}`);
    });
}

// Helper function to convert Map to Array of Objects
function mapToArrayOfObjects(map) {
  return Array.from(map.entries()).map(([id, value]) => ({ id, ...value }));
}

// Helper function to convert Map to Array of usernames
function mapToArrayOfUsernames(playersMap) {
    return Array.from(playersMap.values()).map(player => player.username);
}

function printMapPairs(map) {
    map.forEach((value, key) => {
        console.log(`Key: ${key}, Value: ${JSON.stringify(value)}`);
    });
}

// Increment the score of user
function handleVote(voteUsername) {
    console.log("Vote received for: " + voteUsername + "!");
    numOfVotes++;

    // Find the player by username and update their score
    let playerFound = false;
    players.forEach((player, clientId) => {
        if (player.username === voteUsername) {
            player.currScore += state.round * 100,
            player.totalScore += player.currScore,
            playerFound = true;
            console.log(`Updated current score for ${voteUsername}: ${player.currScore}`);
            console.log(`Updated total score for ${voteUsername}: ${player.totalScore}`);
        }
    });

    if (!playerFound) {
        console.error('Player not found for username:', voteUsername);
    } else {
        // Send updated scores to all clients
        update();
    }
}

//Sends updates to each connected player and non-player.
function update() {
  console.log("Updating players and displays");

  // Convert Maps to Arrays
  const playersArray = mapToArrayOfObjects(players);
  const audienceArray = mapToArrayOfObjects(nonPlayer);

  const commonPayload = { 
    stageRound: state, 
    players: playersArray, 
    nonPlayer: audienceArray 
  };

  // Update each player and non-player
  clientList.clientToSocket.forEach((clientSocket, clientId) => {
    const specificPayload = players.has(clientId) ? { me: players.get(clientId) } : { me: nonPlayer.get(clientId) };
    clientSocket.emit("update", { ...commonPayload, ...specificPayload });
  });

  // Update displays
  displays.forEach(display => display.emit("update", commonPayload));
}

//Handle errors
function error(socket, message, halt) {
    console.log('Error: ' + message);
    socket.emit('fail', message);
    if(halt) {
        socket.disconnect();
    }
}

//Chat message
function handleChat(message) {
    console.log('Handling chat: ' + message); 
    io.emit('chat',message);
}

//Crate a new prompt provided by user
function handleNewPrompt(socket, message) {
  const data = {
    text: message.text,
    username: message.username
  }

  fetch(baseURL+'prompt/create/'+accessCode, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          error(socket, data.msg, false);
      } else {
        localPrompts.push(message);
        console.log("Prompt created for " + message.username);
        socket.emit("prompt", data);
        //console.log("Local prompts: " + localPrompts);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      socket.emit("login", { result: false, message: "Login error" });
    });
}

function addNewConnection(clientSocket, username, password) {
  const newClientNum = nextClientId++;
  clientList.socketToClient.set(clientSocket, newClientNum);
  clientList.clientToSocket.set(newClientNum, clientSocket);

  //TODO: save password as well?
  //TODO: check if in stage 1 as well? assign an audience or playera
  //TODO: make player a class to improve consistency

  // Add player to players list
  if (players.size < PLAYERS_MAX) {
    players.set(newClientNum, {
      username: username, 
      password: password,
      admin: (newClientNum===0),
      currScore: 0,
      totalScore: 0
    });
    return {admin: (newClientNum===0), audience: false, id: newClientNum};
  }
  else {
    nonPlayer.set(newClientNum, {username: username});
    return {admin: (newClientNum===0), audience: true, id: newClientNum};
  }
}

// Populate local prompt list
function getAPIprompts(socket) {

  // Assume the game is always in english
  const data = {
    players: mapToArrayOfUsernames(players),
    language: "en"
  }

  fetch(baseURL+'utils/get/'+accessCode, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          error(socket, data.msg, false);
      } else {
        // Save the prompts with their respective username
        apiPrompts = data
        //console.log('Prompts retrieved from API: ', apiPrompts);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      socket.emit("login", { result: false, message: "Login error" });
    });
}

function distributePromptsForAnswers() {
  console.log("Stage 2 -  GENERATING PROMPTS");
  //console.log("ID: " + id);
  //console.log("LOCAL: " + localPrompts);
  //console.log("API: " + apiPrompts);
  //console.log("ACTIVE: " + activePrompts);
  //console.log("PROMPT: " + JSON.stringify(assignedPrompt));
  //console.log("\n");

  let totalPrompts = [...localPrompts, ...apiPrompts];

  // Even number of players: Assign each prompt to two players
  // Ensure only half of the total prompts are used
  if (players.size % 2 === 0) {
      let promptsForThisRound = totalPrompts.slice(0, players.size / 2);
      promptsForThisRound.sort(() => Math.random() - 0.5);

      //console.log("Prompts for this round (Even):", promptsForThisRound);

      let playerIndex = 0;
      players.forEach((player, clientId) => {
          // Assign each prompt to two players
          const assignedPrompt = promptsForThisRound[playerIndex++ % (players.size / 2)];
          activePrompts.set(clientId, { prompts: [assignedPrompt], answers: [] });
          const clientSocket = clientList.clientToSocket.get(clientId);
          //console.log("Prompt distributed: " + (activePrompts));
          clientSocket.emit("answerPrompts", [assignedPrompt]);
          //console.log("Assigned to player", clientId, ": Prompt", assignedPrompt);
      });
  } else {
      // Pair all prompts for odd players

      //console.log("\nALL PROMPTS: ");
      //printMapPairs(totalPrompts);
      //console.log("\n");

      let promptPairs = [];

      let n = players.size;

      for (let i = 0; i < n; i+=3) {
        if(i + 1 < n) {
          promptPairs.push([totalPrompts[i], totalPrompts[i+1]]);
        }
        if(i + 2 < n) {
          promptPairs.push([totalPrompts[i], totalPrompts[i+2]]);
        }
        if(i + 1 < n && i + 2 < n) {
          promptPairs.push([totalPrompts[i+1], totalPrompts[i+2]]);
        }
      }

      if (n % 3 == 2) {
          promptPairs.push([totalPrompts[n-2], totalPrompts[n-1]]);
      }

      console.log("\nPAIRED PROMPTS: ");
      printMapPairs(promptPairs);
      console.log("\n");

      let promptPairIndex = 0;
      players.forEach((player, clientId) => {
          const assignedPair = promptPairs[promptPairIndex++ % promptPairs.length];
          activePrompts.set(clientId, { prompts: assignedPair, answers: [] });
          const clientSocket = clientList.clientToSocket.get(clientId);
          clientSocket.emit("answerPrompts", assignedPair);
          console.log("Assigned to player", clientId, ": Prompts", assignedPair);
      });
  }
}

function goToNextStage(socket) {
  switch (state.stage) {
    case 1: // Wait for players to join
      getAPIprompts(socket); // Get prompts from API if not empty (should populate the local array by 50%)
      transitionToPrompts(socket);
      break;
    case 2: // Users can input their prompts
      distributePromptsForAnswers(socket);
      transitionToAnswer(socket);
      break;
    case 3: // Answers
      transitionToVotes(socket);
      //console.log("ActivePrompts:", activePrompts);
      //console.log("ActivePrompts size:", activePrompts.size);
      //printMapPairs(activePrompts)
      break;
    case 4: // Votes
      //Move function that does the thing here
      transitionToResults(socket);
      break;
    case 5: // Results
      transitionToScores();
      break;
    case 6: // Scores
      addRoundScoresToTotal();
      transitionToGameOver();
      break;
    case 7: // Game Over
      break;
    default:
      console.error('Unknown game state');
  }
  update(); // Update all the players with the new state
}

function addRoundScoresToTotal() {
  // Find the player by username and update their total score via azure API
  players.forEach((player, clientId) => {

    const socket = clientList.clientToSocket.get(clientId);
    handleScoreUpdate(player.username, player.password, 1, player.currScore, socket);

    console.log(`Updated total score for ${player.username}`);
    player.currScore = 0;
  });
}

function handleScoreUpdate(username, password, gamesPlayed, totalScore, clientSocket) {

  const data = {
    username: username,
    password: password,
    add_to_games_played: gamesPlayed,
    add_to_score: totalScore,
  };

  fetch(baseURL+'player/update/'+accessCode, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          error(clientSocket, data.msg, false);
          console.log('ERROR:', data.msg);
      } else {
        console.log('Total score and games played database update result:', data);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      //clientSocket.emit("", { result: false, message: "" });
    });
}

function getLeaderBoard(n) {
  const data = {
    top: n,
  };

  fetch(baseURL+'utils/leaderboard/'+accessCode, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          console.log('ERROR:', data.msg);
      } else {
        // Send to all clients
        clientList.clientToSocket.forEach(socket => {
            socket.emit('sendLeaderboard', data);
        });
        console.log('Leaderboard get result:', data);
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      //clientSocket.emit("", { result: false, message: "" });
    });
}

function sendResults() {
    players.forEach((player, clientId) => {
        const socket = clientList.clientToSocket.get(clientId);
        if (socket) {
            socket.emit('roundScore', player.currScore);
            socket.emit('sendTotalScore', player.totalScore);
        }
    });
}

//Send the prompts with their answers to players
function sendClientPromptWithAnswers() {
  console.log("Stage 4 - INITIATING VOTES")

  //for reference
  //Key: 0, Value: {"prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"What celebrity is the coolest?","username":"milkdose"}],"answers":[{"milkdose":"mad"}]}
  //Key: 1, Value: {"prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"What celebrity is the coolest?","username":"milkdose"}],"answers":[{"chocdose":"brad"}]}

  //console.log("\nActive: ");
  //printMapPairs(activePrompts);
  //console.log("\n");

  activePrompts.forEach((data, clientId) => {
    let answers = data.answers
    let promptanswerMatch = 0;
    let curr = 0;
    data.prompts.forEach(prompt => {
      //console.log(prompt.id + ", " + prompt.text + ", " + answers[promptanswerMatch]);

      if (promptanswerMatch > 1) {
          promptanswerMatch = 0;
      }

      //Add a prompt to a new list so its singular, if already there - add its answer (max two answers)
      if (!singlePrompts.has(prompt.text)) {
        singlePrompts.set(prompt.text, {"text": prompt.text, "owner": prompt.username,  "answers": [answers[promptanswerMatch]]});
      }
      else {
        singlePrompts.get(prompt.text).answers.push(answers[promptanswerMatch]);
      }
      promptanswerMatch++;
    });
  });

  //This element signifies the end of the prompts to be answered, used to advance to the next round
  singlePrompts.set(999, {"prompts":[{"id":"end","text":"All questions answered!","username":"end"}],"answers":[{"username": "test"},{"username": "test"}]});

  //console.log("\nPaired prompts and answers: ");
  //printMapPairs(singlePrompts);
  //console.log("\n");

  // Send combined prompts and answers to each client for voting
  //singlePrompts.forEach((value, key) => {
  //    io.emit('votePrompt', (key, {"owner": value.owner, "answers": value.answers}));
  //});

  console.log("Prompts to be sent: ");
  printMapPairs(singlePrompts); //Should contain all the prompts with their appropriate answers to be sent to the client

  //Send every message to every client 
  sendCurrentPromptForVoting();
}

function sendCurrentPromptForVoting() {
    if (currentPromptIndex <= singlePrompts.size+1) { //+1 to accomodate final message used as delimiter
        
      let promptArray = Array.from(singlePrompts.values());
      let currentPrompt = promptArray[currentPromptIndex];

      //Send an initial prompt to vote on
      if (initialPrompt) {
        clientList.clientToSocket.forEach(socket => {
            socket.emit('votePrompt', currentPrompt);
        });

        initialPrompt = false;
        currentPromptIndex++;

        clientList.clientToSocket.forEach(socket => {
            socket.emit('votePromptPrev', promptArray[currentPromptIndex-1]);
        });
      }
      
      //console.log(currentPrompt);

      //Check if all users have voted for the current prompt
      if (numOfVotes < players.size) {
        //If not then wait
      }
      else {
        console.log("-> END OF VOTING ROUND: " + (currentPromptIndex+1) + ", " + singlePrompts.size);

        //End the voting rounds 
        if (currentPromptIndex+1 == singlePrompts.size) {
          clientList.clientToSocket.forEach(socket => {
              socket.emit('endOfVotes');
          });
        }

        //Go to state 5 to show results and send client next prompt 
        state.stage = 5; 
        numOfVotes = 0;
        sendResults(); //update round score
        update();

        clientList.clientToSocket.forEach(socket => {
            socket.emit('votePrompt', currentPrompt);
            socket.emit('votePromptPrev', promptArray[currentPromptIndex-1]);
        });
        if (currentPromptIndex+1 == singlePrompts.size) {
          currentPromptIndex = 0;
        }
        else {
          currentPromptIndex++;
        }
      }
    } else {
        //TODO: remove all this? dont think this executes ever
        state.stage = 6;
        update();
    }
}

//Pair all the answers with their respective prompts
function handleAnswer(socket, message) {
  console.log("Stage 3 - COLLECTING ANSWERS")

  /* 
  format:
 
  example:
  Key: 0, Value: { "prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798",
                              "text":"What celebrity is the coolest?",
                              "username":"milkdose"}],
                              "answers":[] }
 
Multiple values answers:
 Key: 2, Value: { "prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"testtesttesttesttest","username":"milkdose"},
                             {"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"tet1tet1tet1tet1tet1","username":"milkdose"}],
                             "answers":[{"chocdose":"test!"},{"chocdose":"teeet1"}]}  <- this is a single user


Simngle question, answered by two players:
Key: 0, Value: {"prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"What celebrity is the coolest?","username":"milkdose"}],"answers":[{"milkdose":"madonna"}]}
Key: 1, Value: {"prompts":[{"id":"bb6b2ab7-3143-42bc-8bab-34eabd352798","text":"What celebrity is the coolest?","username":"milkdose"}],"answers":[{"chochdose":"brad"}]}

*/

    console.log('Server received answer: ' + message.answer + ' from ' + message.username);
    //console.log("-> " + ([...activePrompts]));

    const clientId = clientList.socketToClient.get(socket);
    //if (!clientId) {
    //    console.error('Client ID not found for socket');
    //    return;
    //}

    const playerData = activePrompts.get(clientId);
    if (playerData) {
        // Add the answer to the first prompt that doesn't have an answer yet
        const unansweredPrompt = playerData.prompts.find(p => !playerData.answers.some(a => a[p.id]));
        if (unansweredPrompt) {
            // Append the answer with the username
            playerData.answers.push({ [message.username]: message.answer });
        } else {
            console.error('No unanswered prompt found for client ID:', clientId);
        }
    } else {
        console.error('Active prompts not found for client ID:', clientId);
    }

    //for testing
    //console.log("### START ###");
    //console.log(" ");
    //printMapPairs(activePrompts)
    //console.log(" ");
    //console.log("### END ###");
}

function transitionToResults() {
  state.stage = 5;
}

function transitionToScores() {
  state.stage = 6;
}

function transitionToGameOver() {
  if (state.round < 3) {
    state.round++;
    initialPrompt = true;
    activePrompts.clear();
    singlePrompts.clear();
    numOfVotes = 0;

    players.forEach(player => {
        player.currScore = 0;
    });

    clientList.clientToSocket.forEach(socket => {
        socket.emit('resetVotingEnd');
    });

    state.stage = 2;
    update();
  } else {
    // Send leaderboard to all clients and move onto state 7 to display it
    getLeaderBoard(3);
    state.stage = 7;
  }
}

function transitionToVotes(socket) {
  state.stage = 4;
  sendClientPromptWithAnswers();
}

function transitionToPrompts(socket) {
  //if (players.size >= 3) {
  if (true) {
    state.stage = 2;
  } else { //TODO: uncomment for final deployment
    console.log("Not enough players");
    error(socket, "Need atleast 3 players!", false);
  }
}

function transitionToAnswer(socket) {
  state.stage = 3;
}

// Log the client in
function handleLogin({ username, password }, clientSocket) {
  console.log("Logging in user: " + username);

  // Data to be sent for login verification
  const data = {
    username: username,
    password: password
  };

  fetch(baseURL+'player/login/'+accessCode, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          error(clientSocket, data.msg, false);
      } else {
        console.log('Login result:', data);
        const newClient = addNewConnection(clientSocket, username, password);
        clientSocket.emit("login", {result: true, username: username, password: password, ...newClient});
        update();
        console.log("-> Login data sent to client side");
      }
    })
    .catch((error) => {
      console.error('Error:', error);
      clientSocket.emit("login", { result: false, message: "Login error" });
    });
}

//Register the client
function handleRegister({username, password}, clientSocket) {
  console.log("Registering user: " + username);

  const data = {
    username: username,
    password: password
  };

  fetch(baseURL+'player/register/'+accessCode, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
  })
    .then(response => response.json())
    .then(data => {
      if(data.result === false) {
          error(clientSocket, data.msg, false);
      } else {
        //console.log('Registration result(password hidden):', data)
        const newClient = addNewConnection(clientSocket, username, password);
        //Send 'register' back to client for confirmation, which will auto log in for us
        clientSocket.emit("register", {result: true, username: username, password: password, ...newClient});
        update();
        console.log("-> Register data sent to client side");
      }
    })
    .catch((error) => console.error('Error:', error));

}

//Handle new connection
io.on('connection', socket => { 
  console.log('New connection');

  //Handle register
  socket.on("register", (message) => {
    handleRegister(message, socket);
  });

  //Handle answer 
  socket.on("answer", (message) => {
    handleAnswer(socket, message);
  });

  //Handle login
  socket.on('login', (message) => {
    handleLogin(message, socket);
  });

  //Handle on chat message received
  socket.on('chat', (message) => {
    handleChat(message);
  });
  
  socket.on('prompt', (message) => {
    handleNewPrompt(socket, message);
  });
  
  //Handle disconnection
  socket.on('disconnect', () => {
    console.log('Dropped connection');
  });

  socket.on('vote', (message) => {
    handleVote(message);
  });

  //Advance to the next stage of the game
  socket.on('advance', () => {
    console.log('Advance request received by server');
    goToNextStage(socket);
  });
  
  //Advance to the next stage of the game
  socket.on('goToStage4', () => {
    state.stage = 4;
    update();
  });
  socket.on('goToStage6', () => {
    state.stage = 6;
    update();
  });

  //Advance to the next stage of the game
  socket.on('promptAnswersAck', (message) => {
    console.log('Vote advance request received by server');
    sendCurrentPromptForVoting(message);
  });
  socket.on('advanceVote', () => {
    socket.emit('promptAnswersPaired', singlePrompts);
  });
});


//Start server
if (module === require.main) {
  startServer();
}

module.exports = server;
