var system = require('system');
var fs = require('fs');
var webPage = require('webpage');

if (system.args.length != 4) {
    console.log('Usage: access_adviser.js <signinToken> <arn_file> <output_file>');
    phantom.exit(-1);
}

var iam_url = 'https://console.aws.amazon.com/iam/home?region=us-east-1';
var federation_base_url = 'https://signin.aws.amazon.com/federation';

var signinToken = system.args[1];
var arn_file = system.args[2];
var OUTPUT_FILE = system.args[3];

var arns = JSON.parse(fs.read(arn_file));

var page = webPage.create();
page.settings.userAgent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36';
page.settings.javascriptEnabled = true;
page.settings.loadImages = false;  //Script is much faster with this field set to false
phantom.cookiesEnabled = true;
phantom.javascriptEnabled = true;

page.onConsoleMessage = function(msg) {
    console.log('>>> ' + msg);
};

page.onCallback = function(results) {
  var json_results = JSON.stringify(results, null, 2);
  fs.write(OUTPUT_FILE, json_results, 'w');
  phantom.exit(0);
};

page.onResourceReceived = function(resource) {
    if(resource.url.indexOf("signin.aws.amazon.com") > -1)
    {
      statusCode = resource.status;
    }
};

var getSessionCookies = function(token) {
    var url = federation_base_url + '?Action=login'
                                  + '&Issuer=tripleA'
                                  + '&Destination=' + encodeURIComponent(iam_url)
                                  + '&SigninToken='+token;

    statusCode = 400; // default fail

    var onComplete = function(response) {
        if(statusCode < 400) {
            console.log('Successfully logged in')
            page.includeJs(
                "https://ajax.googleapis.com/ajax/libs/jquery/3.1.0/jquery.min.js",
                function() {
                    page.evaluate(advisor, arns);
                }
            );
        } else {
            console.log('Failed to log in')
            console.log('Account '+response+'. Sample ARN: '+arns[0]);
            phantom.exit(-1);
        }
    };
    page.open(url, function(response) { setTimeout(onComplete, 20000, response) });
};

getSessionCookies(signinToken);

var advisor = function(arns) {
    var PERIOD = 10000; // 10 seconds
    var results = {};
    var progress = {};

    XSRF_TOKEN = window.Csrf.fromCookie(null);
    // XSRF_TOKEN = app.orcaCsrf.token;  

    for (var idx in arns) {
        progress[arns[idx]] = "NOT_STARTED";
    }

    var checkJob = function(jobID, arn) {
        // console.log('Inside checkJob');
        console.log("Checking Job Status for "+jobID+"     "+arn);
        jQuery.ajax({
            type: "POST",
            url: "/iam/service/iamadminproxy/GetServiceLastAccessedDetails",
            dataType: 'json',
            data: '{ "jobID": "'+jobID+'" }',
            beforeSend: function(xhr) {if (XSRF_TOKEN != 'NOT_DEFINED') {xhr.setRequestHeader('X-CSRF-Token', XSRF_TOKEN);} else {system.stderr.writeLine('NOT ADDING XSRF TOKEN');console.log('NOTADDINGCSRF');}},
            success: function (data) {
                var status = data["jobStatus"];
                if (status === 'IN_PROGRESS') {
                    console.log("Job Status for "+arn+" is still IN_PROGRESS");
                    setTimeout(function() { checkJob(jobID, arn) }, PERIOD);
                } else if (status === 'FAILED') {
                    console.log("ERROR GETTING DETAILS on " + arn + ". Skipping...");
                    console.log(JSON.stringify(data));
                    progress[arn] = "ERROR";
                } else {
                    console.log("Job Status for "+arn+" is "+status);
                    results[arn] = data["servicesLastAccessed"]["serviceLastAccessedList"];
                    progress[arn] = "COMPLETE";
                }
            },
            error: function(asdf) {
                console.log("GetServiceLastAccessedDetails ERROR "+arn+". Skipping...");
                console.log(JSON.stringify(asdf));
                progress[arn] = "ERROR";
            }
        });
    };

    var checkProgress = function() {
        for (idx in arns) {
            if (progress[arns[idx]] != "COMPLETE" && progress[arns[idx]] != "ERROR") {
                console.log("Object "+arns[idx]+" is not yet complete. "+progress[arns[idx]]);
                setTimeout(function() { checkProgress() }, PERIOD);
                return;
            }
        }
        console.log("COMPLETE");
        // console.log("Printing Results: "+JSON.stringify(results, null, 2));
        window.callPhantom(results);
    };

    var generateReport = function(arn) {
        console.log("Generating Report for "+arn);
        jQuery.ajax({
            type: "POST",
            url: "/iam/service/iamadminproxy/GenerateServiceLastAccessedDetails",
            dataType: 'json',
            beforeSend: function(xhr) {if (XSRF_TOKEN != 'NOT_DEFINED') {xhr.setRequestHeader('X-CSRF-Token', XSRF_TOKEN);} else {system.stderr.writeLine('NOT ADDING XSRF TOKEN');}},
            data: '{ "arn": "'+arn+'" }',
            success: function (data) {
                // console.log("Generate callback arn: "+arn+" jobid: "+data["jobID"]);
                progress[arn] = "IN_PROGRESS";
                setTimeout(function() { checkJob(data["jobID"], arn) }, PERIOD);
            },
            error: function(asdf) {
                console.log("ERROR GenerateServiceLastAccessedDetails "+arn+". Skipping...");
                console.log(JSON.stringify(asdf));
                progress[arn] = "ERROR";
            }
        });
    };

    for (var idx in arns) {
        generateReport(arns[idx]);
    }
    checkProgress();
};
