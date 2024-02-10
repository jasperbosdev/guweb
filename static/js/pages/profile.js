new Vue({
    el: "#app",
    delimiters: ["<%", "%>"],
    data() {
        return {
            data: {
                stats: {
                    out: [{}],
                    load: true
                },
                flags: window.flags,
                grades: {},
                scores: {
                    recent: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    },
                    best: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    }
                },
                maps: {
                    most: {
                        out: [],
                        load: true,
                        more: {
                            limit: 5,
                            full: true
                        }
                    }
                },
                status: {}
            },
            mode: mode,
            mods: mods,
            modegulag: 0,
            userid: userid,
            playerLevel: 1, // Initialize player level
            levelProgress: 0, // Initialize level progress
            totalScore: 0, // Initialize total score
            level_progress: 0, // Define level_progress within the data object
            totalScoreCount: 0
        };
    },
    created() {
        // starting a page
        this.modegulag = this.StrtoGulagInt();
        // Use Promise.all() to wait for multiple asynchronous operations to complete
        Promise.all([this.LoadProfileData(), this.LoadAllofdata()])
            .then(() => {
                // Once both LoadProfileData() and LoadAllofdata() have completed,
                // call fetchScoresCount()
                this.fetchScoresCount();
            })
            .catch(error => {
                // Handle errors if any of the promises fail
                console.error('Error loading profile data or all data:', error);
            });
        this.LoadUserStatus();
    },
    methods: {
        calculateLevel() {
            // Recalculate total score based on the new mode
            this.totalScore = this.data.stats.out[this.modegulag].tscore;
            // Recalculate player level based on the new total score
            this.playerLevel = this.getLevel(this.totalScore);
        
            // Recalculate level progress based on the new mode and total score
            const currentLevelScore = this.getRequiredScoreForLevel(this.playerLevel);
            const nextLevelScore = this.getRequiredScoreForLevel(this.playerLevel + 1);
            this.level_progress = ((this.totalScore - currentLevelScore) / (nextLevelScore - currentLevelScore)) * 100;
        },        
        getRequiredScoreForLevel(level) {
            if (level <= 100) {
                if (level >= 2) {
                    return (5000 / 3) * (4 * Math.pow(level, 3) - 3 * Math.pow(level, 2) - level) + 1.25 * Math.pow(1.8, level - 60);
                } else {
                    return 1.0; // Should be 0, but we get division by 0 below so set to 1
                }
            } else {
                return 26931190829 + 1e11 * (level - 100);
            }
        },
        getLevel(totalScore) { // Define the function to get the player's level based on total score
            let level = 1;
            while (true) {
                // Avoid endless loops
                if (level > 120) {
                    return level;
                }
        
                // Calculate required score
                const reqScore = this.getRequiredScoreForLevel(level);
        
                // Check if this is our level
                if (totalScore <= reqScore) {
                    // Our level, return it and break
                    return level - 1;
                } else {
                    // Not our level, calculate score for next level
                    level += 1;
                }
            }
        },
        formatAcc(acc) {
            // Ensure acc is a number
            acc = parseFloat(acc);
            // Check if acc is a valid number
            if (!isNaN(acc)) {
              // Round the number to two decimal places
              return Math.round(acc * 100) / 100;
            } else {
              // Return 0 if acc is not a valid number
              return 0;
            }
        },
        destroyChart: function () {
            // get the previous chart instance if it exists
            var previousChart = Chart.getChart('0');

            // destroy the previous chart if it exists
            if (previousChart) {
                previousChart.destroy();
            }
        },
        fetchData: async function () {
            this.destroyChart();
        
            const modDict = {
                'std': { 'vn': 0, 'rx': 4},
                'taiko': { 'vn': 1, 'rx': 5 },
                'catch': { 'vn': 2, 'rx': 6 },
                'mania': { 'vn': 3 }
            };
        
            const realMode = modDict[this.mode][this.mods];
            if(realMode === undefined) return console.error('invalid mods:', this.mods);
            const request = await fetch(`https://api.komako.pw/user_history?id=${userid}&mode=${realMode}&days=193&peak=false`);
            if (!request.ok) {
                const messageElement = document.createElement('div');
                messageElement.id = 'myChartMessage';
                messageElement.innerHTML = `
                    <div class="stats-block">
                        <div class="columns is-marginless">
                            <div class="column is-1">
                                <h1 class="title">:(</h1>
                            </div>
                            <div class="column">
                                <h1 class="title is-6">not enough data</h1>
                                <p class="subtitle is-7">play this mode some more, then come back later</p>
                            </div>
                        </div>
                    </div>
                `;
                const chartContainer = document.getElementById('stats-graph');
                chartContainer.innerHTML = ''; // Clear any previous content
                chartContainer.appendChild(messageElement);
                return;
            }
            const data = await request.json();
            const scoreData = data.result;
            const chartContainer = document.getElementById('stats-graph');
            if(scoreData == null || !scoreData[scoreData.length - 1].pp){
                // if there is no score data, previous_rank is 0 or null or pp is 0, display a message instead of the chart
                const messageElement = document.createElement('div');
                messageElement.id = 'myChartMessage';
                messageElement.innerHTML = `
                    <div class="stats-block">
                        <div class="columns is-marginless">
                            <div class="column is-1">
                                <h1 class="title">:(</h1>
                            </div>
                            <div class="column">
                                <h1 class="title is-6">not enough data</h1>
                                <p class="subtitle is-7">play this mode some more, then come back later</p>
                            </div>
                        </div>
                    </div>
                `;
                chartContainer.innerHTML = ''; // Clear any previous content
                chartContainer.appendChild(messageElement);
                return;
            }
        
            const ppValues = scoreData.map(score => score.pp);
            const canvas = document.createElement('canvas');
            canvas.id = 'myChartCanvas';
            chartContainer.innerHTML = ''; // Clear any previous content
            chartContainer.appendChild(canvas);
        
            const ctx = canvas.getContext('2d');
            const myChart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'global rank',
                        data: scoreData.map(score => ({
                            x: score.time_accessed,
                            y: score.global_rank
                        })),
                        backgroundColor: 'transparent',
                        borderColor: '#F4256A',
                        borderWidth: 9,
                        borderJoinStyle: 'round',
                        pointRadius: 0,
                        pointHitRadius: 60,
                        pointBackgroundColor: '#F4256A',
                        pointHoverBackgroundColor: '#F4256A',
                        pointHoverBorderColor: '#F4256A',
                        showLine: true,
                        lineTension: 0.35
                    }]
                },
                options: {
                    animation: false,
                    plugins: {
                        tooltip: {
                            mode: 'single',
                            caretSize: 10,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    var label = context.dataset.label || '';
                                    label += ': #' + context.parsed.y + '\n(pp: ' + ppValues[context.dataIndex].toLocaleString() + ', ' + moment.unix([context.parsed.x]).fromNow() + ')';
                                    return label;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: false,
                            type: 'time',
                            time: {
                                unit: 'day',
                                displayFormats: {
                                    day: 'MMM d'
                                }
                            },
                            grid: {
                                display: true
                            }
                        },
                        y: {
                            min: 0,
                            reverse: true,
                            display: true,
                            type: 'linear',
                            ticks: {
                                callback: function(value) {
                                    return '#' + value.toFixed(0);
                                }
                            },
                            grid: {
                                display: true // hide y-axis grid lines
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'nearest', 
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    var label = context.dataset.label || '';
                                    label += ': #' + context.parsed.y + ' (pp: ' + ppValues[context.dataIndex] + ', ' + moment.unix([context.parsed.x]).fromNow() + ')';
                                    return label;
                                }
                            }
                        }
                    },
                    maintainAspectRatio: false
                }
            });
        },
        LoadProfileData() {
            return new Promise((resolve, reject) => {
                this.$set(this.data.stats, 'load', true);
                this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_player_info`, {
                        params: {
                            id: this.userid,
                            scope: 'all'
                        }
                    })
                    .then(res => {
                        this.$set(this.data.stats, 'out', res.data.player.stats);
                        this.data.stats.load = false;
                        // Store tscore in a variable accessible within the Vue instance
                        this.totalScore = res.data.player.stats[this.modegulag].tscore;
                        // Call calculateLevel function after obtaining tscore
                        this.calculateLevel();
                        resolve(); // Resolve the promise once data is loaded successfully
                    })
                    .catch(error => {
                        console.error('Error loading profile data:', error);
                        reject(error); // Reject the promise if an error occurs
                    });
            });
        },
        LoadAllofdata() {
            return new Promise((resolve, reject) => {
                this.LoadMostBeatmaps();
                // No need to call fetchScoresCount() here
                this.LoadScores('best');
                this.LoadScores('recent');
                this.fetchData();
        
                // Resolve the promise after all necessary data loading operations
                resolve();
            });
        },
        LoadScores(sort) {
            this.$set(this.data.scores[sort], 'load', true); // Removed unnecessary template literals
            const params = { // Create params object to pass parameters to the API
                id: this.userid,
                mode: this.StrtoGulagInt(),
                scope: sort,
                limit: this.data.scores[sort].more.limit
            };
        
            if (sort === 'recent') {
                const checkbox = document.getElementById('hidefailed');
                const includeFailed = checkbox ? !checkbox.checked : true;
                params.include_failed = includeFailed; // Assign include_failed to params object
            }
        
            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_player_scores`, {
                params: params // Pass params object as the params to the axios request
            })
            .then(res => {
                this.data.scores[sort].out = res.data.scores;
                this.data.scores[sort].load = false; // Added a semicolon here
                this.data.scores[sort].more.full = this.data.scores[sort].out.length !== this.data.scores[sort].more.limit; // Corrected the comparison operator
            })
            .catch(error => {
                console.error("Error fetching scores:", error); // Handle any errors that occur during the axios request
                this.data.scores[sort].load = false; // Ensure that the loading state is set to false even if an error occurs
            });
        },        
        LoadMostBeatmaps() {
            this.$set(this.data.maps.most, 'load', true);
            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_player_most_played`, {
                    params: {
                        id: this.userid,
                        mode: this.StrtoGulagInt(),
                        limit: this.data.maps.most.more.limit
                    }
                })
                .then(res => {
                    this.data.maps.most.out = res.data.maps;
                    this.data.maps.most.load = false;
                    this.data.maps.most.more.full = this.data.maps.most.out.length != this.data.maps.most.more.limit;
                });
        },
        LoadUserStatus() {
            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_player_status`, {
                    params: {
                        id: this.userid
                    }
                })
                .then(res => {
                    this.$set(this.data, 'status', res.data.player_status)
                })
                .catch(function (error) {
                    clearTimeout(loop);
                    console.log(error);
                });
            loop = setTimeout(this.LoadUserStatus, 5000);
        },
        ChangeModeMods: function(mode, mods) {
            if (window.event) {
                window.event.preventDefault();
            }
        
            // Update the mode and mods
            this.mode = mode;
            this.mods = mods;
        
            // Recalculate the modegulag based on the new mode
            this.modegulag = this.StrtoGulagInt();
        
            // Update the data limits
            this.data.scores.recent.more.limit = 5;
            this.data.scores.best.more.limit = 5;
            this.data.maps.most.more.limit = 6;
        
            this.fetchScoresCount();

            // Reload all data and recalculate the level
            this.LoadAllofdata();
            this.calculateLevel();
        },        
        AddLimit(which) {
            if (window.event)
                window.event.preventDefault();

            if (which == 'bestscore') {
                this.data.scores.best.more.limit += 5;
                this.LoadScores('best');
            } else if (which == 'recentscore') {
                this.data.scores.recent.more.limit += 5;
                this.LoadScores('recent');
            } else if (which == 'mostplay') {
                this.data.maps.most.more.limit += 4;
                this.LoadMostBeatmaps();
            }
        },
        actionIntToStr(d) {
            switch (d.action) {
                case 0:
                    return 'Idle: 🔍 Song Select';
                case 1:
                    return '🌙 AFK';
                case 2:
                    return `Playing: 🎶 ${d.info_text}`;
                case 3:
                    return `Editing: 🔨 ${d.info_text}`;
                case 4:
                    return `Modding: 🔨 ${d.info_text}`;
                case 5:
                    return 'In Multiplayer: Song Select';
                case 6:
                    return `Watching: 👓 ${d.info_text}`;
                    // 7 not used
                case 8:
                    return `Testing: 🎾 ${d.info_text}`;
                case 9:
                    return `Submitting: 🧼 ${d.info_text}`;
                    // 10 paused, never used
                case 11:
                    return 'Idle: 🏢 In multiplayer lobby';
                case 12:
                    return `In Multiplayer: Playing 🌍 ${d.info_text} 🎶`;
                case 13:
                    return 'Idle: 🔍 Searching for beatmaps in osu!direct';
                default:
                    return 'Unknown: 🚔 not yet implemented!';
            }
        },
        addCommas(nStr) {
            nStr += '';
            var x = nStr.split('.');
            var x1 = x[0];
            var x2 = x.length > 1 ? '.' + x[1] : '';
            var rgx = /(\d+)(\d{3})/;
            while (rgx.test(x1)) {
                x1 = x1.replace(rgx, '$1' + ',' + '$2');
            }
            return x1 + x2;
        },
        secondsToDhm(seconds) {
            seconds = Number(seconds);
            var dDisplay = `${Math.floor(seconds / (3600 * 24))}d `;
            var hDisplay = `${Math.floor(seconds % (3600 * 24) / 3600)}h `;
            var mDisplay = `${Math.floor(seconds % 3600 / 60)}m `;
            return dDisplay + hDisplay + mDisplay;
        },
        StrtoGulagInt() {
            switch (this.mode + "|" + this.mods) {
                case 'std|vn':
                    return 0;
                case 'taiko|vn':
                    return 1;
                case 'catch|vn':
                    return 2;
                case 'mania|vn':
                    return 3;
                case 'std|rx':
                    return 4;
                case 'taiko|rx':
                    return 5;
                case 'catch|rx':
                    return 6;
                case 'std|ap':
                    return 8;
                default:
                    return -1;
            }
        },
        StrtoModeInt() {
            switch (this.mode) {
                case 'std':
                    return 0;
                case 'taiko':
                    return 1;
                case 'catch':
                    return 2;
                case 'mania':
                    return 3;
            }
        },
        modsStr(mod) {
            const numbermods = [
                {mod_text: "MR", mod_bit: 1 << 30},
                {mod_text: "V2", mod_bit: 1 << 29},
                {mod_text: "2K", mod_bit: 1 << 28},
                {mod_text: "3K", mod_bit: 1 << 27},
                {mod_text: "1K", mod_bit: 1 << 26},
                {mod_text: "KC", mod_bit: 1 << 25},
                {mod_text: "9K", mod_bit: 1 << 24},
                {mod_text: "TG", mod_bit: 1 << 23},
                {mod_text: "CN", mod_bit: 1 << 22},
                {mod_text: "RD", mod_bit: 1 << 21},
                {mod_text: "FI", mod_bit: 1 << 20},
                {mod_text: "8K", mod_bit: 1 << 19},
                {mod_text: "7K", mod_bit: 1 << 18},
                {mod_text: "6K", mod_bit: 1 << 17},
                {mod_text: "5K", mod_bit: 1 << 16},
                {mod_text: "4K", mod_bit: 1 << 15},
                {mod_text: "PF", mod_bit: 1 << 14},
                {mod_text: "AP", mod_bit: 1 << 13},
                {mod_text: "SO", mod_bit: 1 << 12},
                {mod_text: "AU", mod_bit: 1 << 11},
                {mod_text: "FL", mod_bit: 1 << 10},
                {mod_text: "NC", mod_bit: 1 << 9},
                {mod_text: "HT", mod_bit: 1 << 8},
                {mod_text: "RX", mod_bit: 1 << 7},
                {mod_text: "DT", mod_bit: 1 << 6},
                {mod_text: "SD", mod_bit: 1 << 5},
                {mod_text: "HR", mod_bit: 1 << 4},
                {mod_text: "HD", mod_bit: 1 << 3},
                {mod_text: "TD", mod_bit: 1 << 2},
                {mod_text: "EZ", mod_bit: 1 << 1},
                {mod_text: "NF", mod_bit: 1}
            ]
            let mod_text = '';
            let mod_num = 0
            if (!isNaN(mod)) {
                mod_num = mod
                let bit = mod.toString(2)
                let fullbit = "0000000000000000000000000000000".substr(bit.length) + bit
                for (let i = 30; i >= 0; i--) {
                    if (fullbit[i] == 1)  {
                        mod_text += numbermods[i].mod_text
                    }
                }
            } else {
                mod = mod.toUpperCase()
                if (mod !== 'NM') {
                    for (let i = 0; i < mod.length / 2; i++) {
                        let find_mod = numbermods.find(m => m.mod_text == mod.substr(i*2, 2))
                        mod_text += find_mod.mod_text
                        mod_num |= find_mod.mod_bit
                    }
                }
            }
            if (mod_text.includes('NC') && mod_text.includes('DT')) mod_text = mod_text.replace('DT', '');
            if (mod_text.includes('PF') && mod_text.includes('SD')) mod_text = mod_text.replace('SD', '');
            if (mod_num == 0) mod_text += 'NM';
            return mod_text;
        },
        getModPairs(mods_readable) { //mods to image
            const modPairs = [];
            for (let i = 0; i < mods_readable.length; i += 2) {
                modPairs.push(mods_readable.slice(i, i + 2));
            }
            return modPairs;
        },
        getModIconUrl(modPair) {
            const modImageMapping = {
                "AP": "/static/images/mod-icons/AP.png",
                "DT": "/static/images/mod-icons/DT.png",
                "EZ": "/static/images/mod-icons/EZ.png",
                "FL": "/static/images/mod-icons/FL.png",
                "HD": "/static/images/mod-icons/HD.png",
                "HR": "/static/images/mod-icons/HR.png",
                "HT": "/static/images/mod-icons/HT.png",
                "NC": "/static/images/mod-icons/NC.png",
                "NF": "/static/images/mod-icons/NF.png",
                "NM": "/static/images/mod-icons/NM.png",
                "PF": "/static/images/mod-icons/PF.png",
                "RX": "/static/images/mod-icons/RX.png",
                "SD": "/static/images/mod-icons/SD.png",
                "SO": "/static/images/mod-icons/SO.png",
                "TD": "/static/images/mod-icons/TD.png", //touch device
                "TP": "/static/images/mod-icons/TP.png", //target practice (cutting!edge)
                "V2": "/static/images/mod-icons/V2.png", //scorev2 (unranked)
            };
            return modImageMapping[modPair] || ""; // Return empty string if mod pair is not found
        },
        fetchScoresCount() {
            this.$axios.get(`https://api.${domain}/v1/get_player_scores?id=${this.userid}&mode=${this.modegulag}&scope=best&limit=100`)
              .then(res => {
                const scores = res.data.scores;
                this.totalScoreCount = scores.length; // Update totalScoreCount with the actual count from the response
              })
              .catch(error => {
                console.error("Error fetching scores count:", error);
              });
          },
    },
    computed: {}
});

$('html').click(function() {
    console.log('click');
    $('.score-menu').remove();
});

function scoreMenu($this) {
    const score_id = $($this).attr("data--score-id");
    let menu;

    $.ajax({
        url: `https://api.${domain}/get_replay?id=${ score_id }`,
        type: 'GET',
        success: function(response) {
            $($this).append(
                $(`<div class="score-menu" data--score-id="${score_id}" onclick="downloadScore(this);">
                <div class="menu-contents">
                    <i class="fa-solid fa-eye"></i>
                    <span>View details</span>
                </div>
            </div>`)
            );
        },
        error: function(xhr) {
            $($this).append(
                 $(`<div class="score-menu score-unavailable" data--score-id="${score_id}" onclick="downloadScore(this);"><div class="menu-contents"><i class="fa-solid fa-eye"></i><span>View details</span></div></div>`)
            );
        }
    });
}

function downloadScore($this) {
    const score_id = $($this).attr("data--score-id");

    // Open link to download replay using API.
    window.location.href = `${window.location.protocol}//${window.location.hostname}/score/${ score_id }`;
}