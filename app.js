const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const cookieParser = require('cookie-parser');
const querystring = require('querystring');
const path = require('path');

const app = express();
const port = process.env.PORT || 3000;

// Load environment variables from a .env file
require('dotenv').config();

// Spotify Credentials
const client_id = process.env.SPOTIFY_CLIENT_ID;
const client_secret = process.env.SPOTIFY_CLIENT_SECRET;
const redirect_uri = process.env.REDIRECT_URI;

// Middleware
app.use(bodyParser.json());
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.get('/login', (req, res) => {
    const scope = 'user-top-read';
    const authEndpoint = 'https://accounts.spotify.com/authorize';
    const url = `${authEndpoint}?${querystring.stringify({
        response_type: 'code',
        client_id: client_id,
        scope: scope,
        redirect_uri: redirect_uri,
    })}`;
    res.redirect(url);
});

app.get('/callback', async (req, res) => {
    const code = req.query.code || null;
    const authOptions = {
        url: 'https://accounts.spotify.com/api/token',
        form: {
            code: code,
            redirect_uri: redirect_uri,
            grant_type: 'authorization_code'
        },
        headers: {
            'Authorization': 'Basic ' + (Buffer.from(client_id + ':' + client_secret).toString('base64'))
        },
        json: true
    };

    try {
        const response = await axios.post(authOptions.url, querystring.stringify(authOptions.form), { headers: authOptions.headers });
        const access_token = response.data.access_token;
        const refresh_token = response.data.refresh_token;

        // Store tokens in cookies (not recommended for production, use sessions instead)
        res.cookie('access_token', access_token);
        res.cookie('refresh_token', refresh_token);

        res.redirect('/dashboard');
    } catch (error) {
        console.error('Error during Spotify authorization', error);
        res.redirect('/#error=invalid_token');
    }
});

app.get('/dashboard', async (req, res) => {
    const access_token = req.cookies.access_token;

    if (!access_token) {
        return res.redirect('/#error=no_token');
    }

    try {
        const userTopTracks = await axios.get('https://api.spotify.com/v1/me/top/tracks', {
            headers: { 'Authorization': 'Bearer ' + access_token }
        });

        // Process user data and find matches
        // For now, just sending the data back to the client
        res.json(userTopTracks.data);
    } catch (error) {
        console.error('Error fetching user data', error);
        res.redirect('/#error=invalid_token');
    }
});

// Serve the main page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(port, () => {
    console.log(`App is listening at http://localhost:${port}`);
});
