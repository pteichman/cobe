function loggedIn(resp) {
  /* I am not very web 2.0 */
  location.reload();
}

function loggedOut() {
  $.ajax({
    type: "POST",
    url: "/id/logout"
  });

  $(".topbar .email").empty();
  $(".topbar .picture").empty();

  $(".topbar .login").html("<a href='#' onclick='onLoginClicked(); return false;'>Sign in</a>");
}

function onAssertion(assertion) {
  // got a browserid assertion
  if (assertion !== null) {
    $.ajax({
      type: "POST",
      url: "/id/login",
      data: { assertion: assertion },
      success: function(resp, status, xhr) {
        if (resp == null) {
          loggedOut();
        } else {
          loggedIn(resp);
        }
      },
      error: function(resp, status, xhr) {
        alert("login failure" + resp);
      }
    });
  } else {
    loggedOut();
  }
}

function onLoginClicked() {
  navigator.id.getVerifiedEmail(onAssertion);
}

function onLogoutClicked() {
  loggedOut();
}
