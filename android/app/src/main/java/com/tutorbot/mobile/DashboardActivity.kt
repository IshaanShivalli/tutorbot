package com.tutorbot.mobile

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.cardview.widget.CardView

class DashboardActivity : Activity() {

    private lateinit var etServerUrl: EditText
    private lateinit var btnSaveUrl: Button
    private lateinit var cardLaunchChat: CardView
    private lateinit var tvGrade: TextView
    private lateinit var tvSubject: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_dashboard)

        etServerUrl = findViewById(R.id.et_server_url)
        btnSaveUrl = findViewById(R.id.btn_save_url)
        cardLaunchChat = findViewById(R.id.card_launch_chat)
        tvGrade = findViewById(R.id.tv_grade)
        tvSubject = findViewById(R.id.tv_subject)

        // Load persisted Server URL
        val prefs = getSharedPreferences("TutorBotPrefs", Context.MODE_PRIVATE)
        val savedUrl = prefs.getString("server_url", "http://192.168.157.254:5000/")
        etServerUrl.setText(savedUrl)

        // Handle URL update
        btnSaveUrl.setOnClickListener {
            val inputUrl = etServerUrl.text.toString().trim()
            if (inputUrl.isNotEmpty()) {
                prefs.edit().putString("server_url", inputUrl).apply()
                Toast.makeText(this, "Endpoint updated successfully!", Toast.LENGTH_SHORT).show()
            } else {
                Toast.makeText(this, "URL cannot be empty", Toast.LENGTH_SHORT).show()
            }
        }

        // Navigate to MainActivity (WebView chat room)
        cardLaunchChat.setOnClickListener {
            val finalUrl = etServerUrl.text.toString().trim()
            val intent = Intent(this, MainActivity::class.java).apply {
                putExtra("URL", finalUrl)
            }
            startActivity(intent)
        }
    }
}
