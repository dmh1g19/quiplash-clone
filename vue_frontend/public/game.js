var socket = null;

//Prepare game
var app = new Vue({
    el: '#game',
    data: {
        voteSubmitted: false,
        error: null,
        isRegistering: false,
        connected: false,
        messages: [],
        submittedPrompt: '',
        answer: '',
        players: [],
        audience: [],
        username: '',
        password: '',
        chatmessage: '',
        curr: null,
        loggedIn: false,
        me: {admin: false, score: 0, state: 0, audience: false, id: null},
        stageRound: {stage: 1, round: 1},
        promptToAnswer: null,
        promptsToAnswer: [], 
        votingPrompt: '',
        promptPrevious: '',
        votedUser: '',
        currScore: 0,
        totalScore: 0,
        votingEnd: false,
        answers: [],
        leaderboard: [],
        answersSubmitted: false
    },
    mounted: function() {
        connect(); 
    },
    methods: {
        handleChat(message) {
            if(this.messages.length + 1 > 10) {
                this.messages.pop();
            }
            this.messages.unshift(message);
        },
        chat() {
            socket.emit('chat',this.chatmessage);
            this.chatmessage = '';
        },
        advance() {
            socket.emit('advance');
        },
        advanceStage5() {
            socket.emit('goToStage4');
        },
        advanceStage6() {
            socket.emit('goToStage6');
        },
        advanceVote() {
            socket.emit('advanceVote');
        },
        makePrompt() {
            socket.emit('prompt', {text: this.submittedPrompt, username: this.username});
        },
        handleCreatePromptConfirm() {
            // Disable any more prompt input after user submits by changing user state
            this.me.state = 1;
            this.update();
        },
        makeAnswer() {
            socket.emit('answer', {answer: this.answer,  username: this.username});
        },
        receivePrompt(message) { // Prompt to be anwered
            console.log("CLIENT: " + message.username + " assigned prompt: " + message.text);
            app.promptToAnswer = message;
        },
        login() {
            this.me.state = 1; //change state to joining 
            socket.emit('login', {username: this.username, password: this.password});
            this.isRegistering = false;
        },
        submitAnswer() {
            socket.emit('answer', { answer: this.answer, username: this.username });
            this.answer = '';
        },
        register() {
            this.me.state = 1; //change state to joining 
            socket.emit('register', {username: this.username, password: this.password});
            this.isRegistering = true;
        },
        updateLoggedIn(message) {
            if(message.result == false) {return;}
            this.me.state = 0;
            this.loggedIn = true;
            this.username = message.username;
            this.me.admin = message.admin;
            this.me.audience = message.audience;
            this.me.id = message.id;
        },
        fail(message) {
            this.error = message;
            setTimeout(clearError, 2000);
        },
        receivePrompts(prompts) {
            this.promptsToAnswer = prompts;
            //this.answers = new Array(prompts.length).fill(''); // Initialize answers array
            this.answers = prompts.map(() => ''); // Initialize answers array
        },
        setPrevPrompt(prompt) {
            this.promptPrevious = prompt;
        },
        submitAnswers() {
            this.promptsToAnswer.forEach((prompt, index) => {
                socket.emit('answer', { prompt: prompt, answer: this.answers[index], username: this.username });
            });

            this.answersSubmitted = true; //remove submit button after answering prompt

            // Reset prompts and answers after submission
            this.promptsToAnswer = [];
            this.answers = [];
        },
        getVote(userVotedFor) {
            socket.emit('vote', userVotedFor);

            // Handle post-vote actions
            this.votedUser = userVotedFor;
            this.voteSubmitted = true;
        },
        receiveVotePrompt(voteData) {
            //Assign prompt locally to be displayed to player
            this.votingPrompt = voteData;
            this.voteSubmitted = false;
        },
        sendPromptsWithAnswers(message) {
            socket.emit('promptAnswersAck', message);
        },
        updateCurrScore(message) {
            this.currScore = message;
        },
        endOfVotes() {
            this.votingEnd = true;
        },
        resetEndOfVotes() {
            this.votingEnd = false;
        },
        updateTotalScore(message) {
            this.totalScore = message;
        },
        handleLeaderBoard(message) {
            this.leaderboard = message;
        },
        update() {
            this.me = this.me;
            this.stageRound = this.stageRound;
            this.player_state = this.player_state;
            this.players = this.players;
            this.audience = this.audience;
            this.username = this.username;
            this.id = this.id;
        }
    }
});

function connect() {
    //Prepare web socket
    socket = io();

    //Receive messages from server
    socket.on('fail', function(message) {
        app.fail(message);
    }); 
    
    //Receive the prompt that this user has to answer
    socket.on('answerPrompt', function(message) {
        app.receivePrompt(message);
    }); 

    socket.on('roundScore', function(message) {
        app.updateCurrScore(message);
    }); 

    socket.on('answerPrompts', function(prompts) {
        app.receivePrompts(prompts);
    });

    socket.on('votePrompt', function(voteData) {
        app.receiveVotePrompt(voteData);
    });

    socket.on('endOfVotes', function(voteData) {
        app.endOfVotes(voteData);
    });
    
    socket.on('resetVotingEnd', function(voteData) {
        app.resetEndOfVotes();
    });
    
    // Confirm when a new prompt has been submitted
    socket.on('promptAnswersPaired', function(promptsWithAnswers) {
        app.sendPromptsWithAnswers(promptsWithAnswers);
    }); 
    
    // Confirm when a new prompt has been submitted
    socket.on('prompt', function(message) {
        app.handleCreatePromptConfirm();
    }); 

    //Connect
    socket.on('connect', function() {
        //Set connected state to true
        app.connected = true;
    });

    //Handle connection error
    socket.on('connect_error', function(message) {
        alert('Unable to connect: ' + message);
    });

    //Handle disconnection
    socket.on('disconnect', function() {
        alert('Disconnected');
        app.connected = false;
    });

    //Handle incoming chat message
    socket.on('chat', function(message) {
        app.handleChat(message);
    });

    //Handle user's answers to prompts
    socket.on('answer', (message) => {
        submitAnswer(socket, message);
    });
    
    //Handle user's answers to prompts
    socket.on('sendTotalScore', (message) => {
        app.updateTotalScore(message);
    });

    socket.on('update', function(message) {
        if (message.stageRound.state != app.stageRound.state) { // Reset player state if game state changes TODO: delete this
            app.me.state = 0;
        }
        app.players = message.players;
        app.stageRound = message.stageRound;
        app.curr = {...app.curr, ...message.curr}; 
        app.me = {...app.me, ...message.me}; 
        app.answersSubmitted = false;
        app.update();
    });

    //Update everything when someone registers or logs in
    socket.on('votePromptPrev', function(message) {
        app.setPrevPrompt(message);
    });

    //Update everything when someone registers or logs in
    socket.on('register', function(message) {
        app.updateLoggedIn(message);
    });

    socket.on('login', function(message) {
        app.updateLoggedIn(message);
    });

    socket.on('sendLeaderboard', function(message) {
        app.handleLeaderBoard(message);
    });
}