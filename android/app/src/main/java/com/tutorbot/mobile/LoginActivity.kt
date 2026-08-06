package com.tutorbot.mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast

class LoginActivity : Activity() {

    private lateinit var etUsername: EditText
    private lateinit var etPassword: EditText
    private lateinit var btnAuthSubmit: Button
    private lateinit var tvModeHelper: TextView
    private lateinit var tvSwitchMode: TextView
    private lateinit var authSubtitle: TextView

    private var isSignUpMode = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Session check
        val prefs = getSharedPreferences("TutorBotPrefs", Context.MODE_PRIVATE)
        if (prefs.getBoolean("is_logged_in", false)) {
            startActivity(Intent(this, DashboardActivity::class.java))
            finish()
            return
        }

        setContentView(R.layout.activity_login)

        etUsername = findViewById(R.id.et_username)
        etPassword = findViewById(R.id.et_password)
        btnAuthSubmit = findViewById(R.id.btn_auth_submit)
        tvModeHelper = findViewById(R.id.tv_mode_helper)
        tvSwitchMode = findViewById(R.id.tv_switch_mode)
        authSubtitle = findViewById(R.id.auth_subtitle)

        // Switch modes
        tvSwitchMode.setOnClickListener {
            isSignUpMode = !isSignUpMode
            if (isSignUpMode) {
                authSubtitle.text = "Create your custom study space setup"
                btnAuthSubmit.text = "Sign Up"
                tvModeHelper.text = "Already have an account?"
                tvSwitchMode.text = " Log In"
            } else {
                authSubtitle.text = "Your Premium AI Study Space"
                btnAuthSubmit.text = "Log In"
                tvModeHelper.text = "New to TutorBot?"
                tvSwitchMode.text = " Create Account"
            }
        }

        // Submit credentials
        btnAuthSubmit.setOnClickListener {
            val username = etUsername.text.toString().trim()
            val password = etPassword.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please enter all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (password.length < 4) {
                Toast.makeText(this, "Password must be at least 4 characters", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // Save login session details
            prefs.edit().apply {
                putBoolean("is_logged_in", true)
                putString("username", username)
                apply()
            }

            Toast.makeText(this, if (isSignUpMode) "Sign Up Successful!" else "Login Successful!", Toast.LENGTH_SHORT).show()

            // Navigate to Dashboard
            startActivity(Intent(this, DashboardActivity::class.java))
            finish()
        }
    }
}
