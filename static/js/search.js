function handleFocus() {
    $('#search-txt').css('min-width', '350px');
    $('#search-results').fadeIn();
    $('#search-results').css('visibility', 'visible');
  }
  
  function handleBlur() {
    if (inputElement.value !== "") {
      return;
    } else {
      $('#search-txt').css('min-width', '0vw');
      $('#search-results').fadeOut();
    }
  }
  
  function search() {
    const searchtxt = document.getElementById("search-txt").value;
    const domain = 'meow.nya';
    if (searchtxt === "" || searchtxt === " ") {
      return;
    } else {
      $.ajax({
        url: `https://api.${domain}/v1/search?q=${searchtxt}`,
        type: 'GET',
        success: function (data) {
          const parentElement = document.getElementById('search-results');
          parentElement.innerHTML = '';
          for (let i = 0; i < data.results; i++) {
            const wrapper = document.createElement('div');
            wrapper.setAttribute('class', 'result-wrapper');
            wrapper.setAttribute('id', `result${i}`);
            wrapper.setAttribute('style', `background-image: linear-gradient(hsl(0, 10%, 10%, 50%), hsl(0, 10%, 10%, 80%)), url(/banners/${data.result[i].id}); background-size: cover; background-position-y: center;`);
            wrapper.addEventListener('click', function() {
              location.href = `https://${domain}/u/${data.result[i].id}`;
            });
            const image = document.createElement('div');
            image.setAttribute('id', 'result-image');
            image.setAttribute('style', `background-image: url(https://a.${domain}/${data.result[i].id});`);
            const name = document.createElement('p');
            name.setAttribute('id', 'result-name');
            name.setAttribute('style', 'text-shadow: 1px 5px 7px #000000;')
            name.innerHTML = data.result[i].name;
            parentElement.appendChild(wrapper);
            wrapper.appendChild(image);
            wrapper.appendChild(name);
          }
        },
        error: function() {
          const parentElement = document.getElementById('search-results');
          parentElement.innerHTML = '';
          const name = document.createElement('p');
          name.setAttribute('id', 'nothing');
          name.innerText = 'nothing found!';
          parentElement.appendChild(name);
        }
      });
    }
  }
  
  const inputElement = document.getElementById('search-txt');
  if (inputElement) {
      inputElement.addEventListener('focus', handleFocus);
      inputElement.addEventListener('blur', handleBlur);
      inputElement.addEventListener('change', search);
  }
  
  $("#search-txt").on('keyup keydown', function (e) {
    search();
  });
  
  // Define a variable to hold the timeout
  let closeTimeout;
  
  // Close search when clicking outside of it
  $(document).on('click', function(event) {
    if (!$(event.target).closest('#search-box').length) {
      // If the timeout is set, clear it
      if (closeTimeout) {
        clearTimeout(closeTimeout);
      }
      // Set a timeout to close the search box after 200ms
      closeTimeout = setTimeout(function() {
        $('#search-txt').css('min-width', '0vw');
        $('#search-results').fadeOut();
      }, 2000000000);
    }
  });
  
  // Cancel the timeout if the search box is clicked
  $('#search-box').on('click', function(event) {
    clearTimeout(closeTimeout);
  });
  
  