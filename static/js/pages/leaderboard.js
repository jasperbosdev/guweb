new Vue({
    el: "#app",
    delimiters: ["<%", "%>"],
    data() {
        return {
            flags: window.flags,
            boards : {},
            mode : 'std',
            mods : 'vn',
            sort : 'pp',
            country : 'all',
            load : false,
            no_player : false, // soon
        };
    },
    created() {
        this.LoadData(mode, mods, sort);
        this.LoadLeaderboard(sort, mode, mods);
    },
    methods: {
        getCountryName(countryCode) {
            return this.flags[countryCode.toUpperCase()] || "Unknown Country";
        },
        LoadData(mode, mods, sort, country) {
            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
            this.$set(this, 'sort', sort);
            this.$set(this, 'country', country);
        },
        LoadLeaderboard(sort, mode, mods, country) {
            if (window.event)
                window.event.preventDefault();
            
            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
            this.$set(this, 'sort', sort);
            this.$set(this, 'country', country);
            this.$set(this, 'load', true);
        
            let params = {
                mode: this.StrtoGulagInt(),
                sort: this.sort
            };
        
            if (country && country !== 'all') {
                params.country = country;
            }
        
            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_leaderboard`, { params })
                .then(res => {
                    this.boards = res.data.leaderboard;
                    this.$set(this, 'load', false);
                    this.togglecountry(this.country);
                });
        },
        scoreFormat(score) {
            var addCommas = this.addCommas;
            if (score > 1000 * 1000) {
                if (score > 1000 * 1000 * 1000)
                    return `${addCommas((score / 1000000000).toFixed(2))} billion`;
                return `${addCommas((score / 1000000).toFixed(2))} million`;
            }
            return addCommas(score);
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
        togglecountry(country) {
            var banner = document.getElementById("lb-name");
            if (banner) {
                if (country && country !== 'all') {
                    var countryName = this.flags[country.toUpperCase()] || "Unknown Country";
                    banner.innerHTML = `<img id="lb-flag" class="player-flag" src="/static/images/flags/${country.toUpperCase()}.png" style="margin-right: 8px;">${countryName} Leaderboard`;
                } else {
                    banner.innerText = `Leaderboard`;
                    this.LoadLeaderboard(this.sort, this.mode, this.mods, 'all');
                }
            } else {
                console.error("Banner element not found.");
            }
        },
        StrtoGulagInt() {
            switch (this.mode + "|" + this.mods) {
                case 'std|vn': return 0;
                case 'taiko|vn': return 1;
                case 'catch|vn': return 2;
                case 'mania|vn': return 3;
                case 'std|rx': return 4;
                case 'taiko|rx': return 5;
                case 'catch|rx': return 6;
                case 'std|ap': return 8;
                default: return -1;
            }
        },
    },
    computed: {}
});
