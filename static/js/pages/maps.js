const inputElement2 = document.getElementById('beatmap-search-txt');
let timeoutId = null;

function handleFocus() {
    $('#beatmap-search-txt').css('min-width', '350px');
    $('#beatmap-search-results').fadeIn();
    $('#beatmap-search-results').css('visibility', 'visible');
}

function intToMode(mode) {
  switch (mode) {
    case 0:
      return 'osu';
    case 1:
      return 'taiko';
    case 2:
      return 'catch';
    case 3:
      return 'mania';
    default:
      return 'osu';
  }
}

function difficultyColourSpectrum(diffValue) {
  const domain = [0.1, 1.25, 2, 2.5, 3.3, 4.2, 4.9, 5.8, 6.7, 7.7, 9];
  const range = ['#4290FB', '#4FC0FF', '#4FFFD5', '#7CFF4F', '#F6F05C', '#FF8068', '#FF4E6F', '#C645B8', '#6563DE', '#18158E', '#000000'];
  let color = '';
  for (let i = 0; i < domain.length - 1; i++) {
    if (diffValue >= domain[i] && diffValue < domain[i + 1]) {
      const t = (diffValue - domain[i]) / (domain[i + 1] - domain[i]);
      color = d3.interpolateRgb.gamma(2.2)(range[i])(t);
      break;
    }
  }
  if (color === '') {
    color = range[range.length - 1];
  }
  return color;
}

function handleBlur() {
    if (inputElement2.value !== "") {
        return;
    } else {
        $('#beatmap-search-txt').css('min-width', '0vw');
        $('#beatmap-search-results').fadeOut();
    }
}

function searchBeatmaps() {
    const searchtxt = document.getElementById("beatmap-search-txt").value;
    const domain = 'meow.nya';

    if (searchtxt === "" || searchtxt === " " || searchtxt.length < 3) {
        return;
    } else {
        $.ajax({
            url: `https://api.${domain}/v1/search_beatmaps?q=${searchtxt}`,
            type: 'GET',
            success: function (response) {
                const results = response.result; // access the 'result' key in the response
                const parentElement = document.getElementById('beatmap-search-results');
                parentElement.innerHTML = '';

                // group beatmaps with the same set_id
                const groupedResults = {};
                for (let i = 0; i < results.length; i++) {
                    const setId = results[i].set_id;
                    if (groupedResults.hasOwnProperty(setId)) {
                        groupedResults[setId].push(results[i]);
                    } else {
                        groupedResults[setId] = [results[i]];
                    }
                }

                // iterate over the grouped results
                for (const setId in groupedResults) {
                    if (groupedResults.hasOwnProperty(setId)) {
                        const beatmaps = groupedResults[setId];
                        const wrapper = document.createElement('div');
                        wrapper.setAttribute('class', 'result-wrapper-maps');
                        wrapper.setAttribute('style', `background-image: linear-gradient(hsl(var(--main), 300%, 15%, 25%), #2A222A), url(https://assets.ppy.sh/beatmaps/${beatmaps[0].set_id}/covers/cover.jpg)`);
                        const name = document.createElement('p');
                        name.setAttribute('id', 'beatmap-result-name');
                        name.setAttribute('style', 'text-shadow: 1px 5px 7px #000000;');
                        // set fontawesome icons and colors based on the status value
                        let iconClass = "";
                        let iconColor = "";
                        switch (beatmaps[0].status) {
                            case 0:
                                iconClass = "fas fa-question";
                                iconColor = "#ffffff"; // white
                                break;
                            case 2:
                                iconClass = "fas fa-angles-up";
                                iconColor = "#0080ff"; // blue
                                break;
                            case 3:
                                iconClass = "fas fa-check";
                                iconColor = "#00cc00"; // green
                                break;
                            case 5:
                                iconClass = "fas fa-heart";
                                iconColor = "#ff69b4"; // pink
                                break;
                            default:
                                iconClass = "fas fa-question";
                                iconColor = "#ffffff"; // white
                        }
                        const icon = document.createElement('i');
                        icon.setAttribute('class', iconClass);
                        icon.setAttribute('style', `color: ${iconColor}; font-size: 1.2em; margin-right: 0.5em`);
                        name.appendChild(icon);

                        // create the difficulty list
                        const difficultyList = document.createElement('ul');
                        difficultyList.setAttribute('class', 'difficulty-list');

                        beatmaps.sort((a, b) => parseFloat(a.diff) - parseFloat(b.diff));

                        beatmaps.forEach((beatmap) => {
                          const listItem = document.createElement('li');
                          const difficultyLink = document.createElement('a');
                          difficultyLink.setAttribute('href', `https://${domain}/b/${beatmap.id}`);
                          
                          const modeIcon = document.createElement('span');
                          modeIcon.setAttribute('class', `mode-icon mode-${intToMode(beatmap.mode)}`);

                          const color = difficultyColourSpectrum(parseFloat(beatmap.diff));
                          modeIcon.setAttribute('style', `color: ${color};margin-right: 15px;`);

                          difficultyLink.appendChild(modeIcon);

                          const difficultyName = document.createElement('span');
                          difficultyName.classList.add('hidden');
                          difficultyName.appendChild(document.createTextNode(beatmap.version));
                          difficultyLink.appendChild(difficultyName);
                          
                          listItem.appendChild(difficultyLink);
                          difficultyList.appendChild(listItem);
                        });

                        name.innerHTML += `${beatmaps[0].artist} - ${beatmaps[0].title}<br>mapped by ${beatmaps[0].creator}<br>`;
                        name.appendChild(difficultyList);
                        parentElement.appendChild(wrapper);
                        wrapper.appendChild(name);
                    }
                }
            },
            error: function () {
                const parentElement = document.getElementById('beatmap-search-results');
                parentElement.innerHTML = '';
                const name = document.createElement('p');
                name.setAttribute('id', 'beatmap-nothing');
                name.innerText = 'nothing found!';
                parentElement.appendChild(name);
            }
        });
    }
}

inputElement2.addEventListener('focus', handleFocus);
inputElement2.addEventListener('blur', handleBlur);
inputElement2.addEventListener('change', searchBeatmaps);
inputElement2.addEventListener('keyup', function (e) {
    clearTimeout(timeoutId);
    if (inputElement2.value.length >= 3) {
        timeoutId = setTimeout(searchBeatmaps, 500);
    }
});