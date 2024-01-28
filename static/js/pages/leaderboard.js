new Vue({
    el: "#app",
    delimiters: ["<%", "%>"],
    data() {
        return {
            flags: window.flags,
            boards: {},
            mode: 'std',
            mods: 'vn',
            sort: 'pp',
            country: 'all',
            currentPage: 1,
            totalPages: 1,
            load: false,
            no_player: false, // soon
            showCountryMenu: false,
            countries: [],
            limit: 25
        };
    },
    created() {
        window.addEventListener('click', this.handleClickOutside);
        // Get countries from vue-flags.js
        this.countries = Object.keys(window.flags).map(countryCode => ({
            code: countryCode,
            flag: `/static/images/flags/${countryCode}.png`,
            name: this.flags[countryCode] || "Unknown Country"
        }));
        this.LoadData(this.mode, this.mods, this.sort);
        this.LoadLeaderboard(this.sort, this.mode, this.mods);
    },
    methods: {
        getCountryName(countryCode) {
            return this.flags[countryCode.toUpperCase()] || "";
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
                sort: this.sort,
                limit: this.limit,
                page: this.currentPage
            };

            if (country && country !== 'all') {
                params.country = country;
            }

            this.$axios.get(`${window.location.protocol}//api.${domain}/v1/get_leaderboard`, { params })
            .then(res => {
                this.boards = res.data.leaderboard;
                this.$set(this, 'load', false);
                this.togglecountry(this.country);
        
                // Calculate total pages based on total items and limit per page
                this.totalPages = res.data.total_pages || 1; // Use total_pages property from API response
            })
            .catch(error => {
                console.error('Error loading leaderboard:', error);
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
        nextPage() {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.LoadLeaderboard(this.sort, this.mode, this.mods, this.country);
            }
        },
        prevPage() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.LoadLeaderboard(this.sort, this.mode, this.mods, this.country);
            }
        },
        toggleCountryMenu() {
            this.showCountryMenu = !this.showCountryMenu;
            console.log("Country menu toggled. Show menu:", this.showCountryMenu);
        },
        selectCountry(countryCode) {
            this.showCountryMenu = false;
            this.LoadLeaderboard(this.sort, this.mode, this.mods, countryCode);
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
        handleClickOutside(event) {
            const modal = document.querySelector('.country-modal-content');
            if (modal && !modal.contains(event.target)) {
                this.showCountryMenu = false;
            }
        },
        formatPlaytime(timestamp) {
            const seconds = Math.floor(timestamp % 60);
            const minutes = Math.floor((timestamp / 60) % 60);
            const hours = Math.floor((timestamp / (60 * 60)) % 24);
            const days = Math.floor(timestamp / (60 * 60 * 24));
    
            let result = '';
            if (days > 0) result += `${days}d `;
            if (hours > 0) result += `${hours}h `;
            if (minutes > 0) result += `${minutes}m `;
    
            return result.trim();
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
    computed: {
        isAdditionalCountrySelected() {
            return this.country !== 'all' && !['NL', 'US', 'RU', 'KR', 'PL', 'GB', 'NZ'].includes(this.country);
        },
    }
});

Vue.component('user-profile', {
    props: ['user', 'mode', 'domain'],
    template: `
    <span :id="user.player_id" class="user-name" @mouseover="showProfile" @mouseout="hideProfile">
        <a :href="'/u/'+user.player_id+'?mode='+mode+'&mods='+mods">
          <div class="player-avatar" :style="'background-image: url(https://a.' + domain + '/' + user.player_id + ')'"></div>
          <a :title="flags[user.country.toUpperCase()]" :style="'background-image: url(/static/images/flags/' + user.country.toUpperCase() + '.png)'" class="player-flag">
            <div class="flag-dropdown">
              {{ flags[user.country.toUpperCase()] }}
            </div>
          </a>
          {{ user.name }}
        </a>
        <div class="profile-panel" v-bind:style="{ display: profileStyle }">
            <div class="profile-panel-avatar" :style="'background-image: url(https://a.' + domain + '/' + user.player_id + ')'"></div>
            <div class="profile-panel-background" :style="'background: linear-gradient(rgba(71, 67, 67, 0.5) 0%, rgba(71, 67, 67, 0) 100%) 50% / cover, linear-gradient(rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0.6) 100%), url(https://' + domain + '/banners/' + user.player_id + '); background-size: cover; background-position-y: center;'"></div>
            <div class="profile-panel-info">
            <div class="name">
              {{ user.name }}
            </div>
            <div class="activity">
              Last seen {{ formatTimeAgo(user.latest_activity) }}
            </div>
            </div>
        </div>
    </span>
    `,
    data: function() {
        return {
            profileVisible: false,
            badgePopupVisible: false,
            badgePopupTop: 0,
            badgePopupLeft: 0,
        };
    },
    methods: {
        showProfile: function() {
            this.profileVisible = true;
        },
        hideProfile: function() {
            this.profileVisible = false;
        },
        showBadgePopup: function(event, badge) {
            if (this.badgePopupVisible != badge.id) {
                this.badgePopupVisible = badge.id;
                // Calculate the position of the badge popup relative to the badge icon
                const badgeIcon = event.target;
                const badgeIconRect = badgeIcon.getBoundingClientRect();
                this.badgePopupTop = badgeIconRect.top + badgeIconRect.height + 'px';
                this.badgePopupLeft = badgeIconRect.left + 'px';
            }
        },
        hideBadgePopup: function() {
            this.badgePopupVisible = false;
        },
        formatTimeAgo: function(timestamp) {
            const now = new Date().getTime();
            const secondsPast = Math.floor((now - timestamp * 1000) / 1000);
        
            if (secondsPast < 60) {
                return parseInt(secondsPast) + 's ago';
            } else if (secondsPast < 3600) {
                return parseInt(secondsPast / 60) + 'm ago';
            } else if (secondsPast < 86400) {
                return parseInt(secondsPast / 3600) + 'h ago';
            } else if (secondsPast < 2592000) { // 30 days (roughly a month)
                const days = Math.floor(secondsPast / (3600 * 24));
                return days > 1 ? days + ' days ago' : '1 day ago';
            } else if (secondsPast < 31536000) { // 365 days (roughly a year)
                const months = Math.floor(secondsPast / (3600 * 24 * 30));
                return months > 1 ? months + ' months ago' : '1 month ago';
            } else {
                const years = Math.floor(secondsPast / 31536000);
                return years > 1 ? years + ' years ago' : '1 year ago';
            }
        },
    },
    computed: {
        profileStyle: function() {
            return this.profileVisible ? 'flex !important' : 'none !important';
        }
    }
});
