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
            return this.flags[countryCode.toUpperCase()] || "";
        },
        LoadData(mode, mods, sort) {
            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
            this.$set(this, 'sort', sort);
        },
        LoadLeaderboard(sort, mode, mods) {
            if (window.event)
                window.event.preventDefault();

            //window.history.replaceState('', document.title, `/leaderboard/${this.mode}/${this.sort}/${this.mods}`);
    
            let owo = window.location.href.split('/')[4];

            this.$set(this, 'mode', mode);
            this.$set(this, 'mods', mods);
            this.$set(this, 'sort', sort);
            this.$set(this, 'load', true); // https://api.komako.pw/get_map_scores?id=2625702&scope=best
            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_map_scores`, { params: {
                id: owo,
                mode: this.StrtoGulagInt(),
                mods: this.mods,
                scope: "best"
            }}).then(res => {
                this.boards = res.data.scores;
                this.$set(this, 'load', false);
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
        scoreFormatFirstPlace(score) {
            var addCommas = this.addCommas;
            if (score > 1000 * 1000) {
                if (score > 1000 * 1000 * 1000)
                    return `${addCommas((score / 1000000000).toFixed(2))}b`;
                return `${addCommas((score / 1000000).toFixed(2))}m`;
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
        secondsToDhm(seconds) {
            seconds = Number(seconds);
            var h = Math.floor(seconds % (3600*24) / 3600);
            var m = Math.floor(seconds % 3600 / 60);
            
            var sDisplay = seconds % 60 >= 10 ? seconds % 60 : "0" + seconds % 60;
            var hDisplay = h + ":";
            var mDisplay = m + ":";
            return h > 0 ? hDisplay : "" + mDisplay + sDisplay;
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