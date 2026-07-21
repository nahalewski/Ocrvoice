package com.dcops.fibertrainer;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.view.KeyEvent;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ValueCallback;
import android.webkit.WebView;
import android.webkit.WebSettings;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Tint the status bar to match the app's navy top bar.
        Window w = getWindow();
        w.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        w.setStatusBarColor(Color.parseColor("#12233b"));

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // localStorage for saved progress
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setAllowFileAccess(true);
        s.setTextZoom(100);
        web.setBackgroundColor(Color.parseColor("#eef2f7"));

        // Keep all navigation inside the WebView (named class avoids d8 issues).
        web.setWebViewClient(new AppWebViewClient());

        web.loadUrl("file:///android_asset/index.html");
    }

    // Route the hardware Back button to the web app's own history first.
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            web.evaluateJavascript(
                "(window.onAndroidBack && window.onAndroidBack())",
                new BackCallback());
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    /** Keeps link navigation inside the WebView. */
    private static class AppWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            view.loadUrl(url);
            return true;
        }
    }

    /** Finishes the activity only when the web app has no history left. */
    private class BackCallback implements ValueCallback<String> {
        @Override
        public void onReceiveValue(String value) {
            if (!"true".equals(value)) {
                finish();
            }
        }
    }
}
