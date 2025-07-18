# Telegram Alert Setup Guide

This guide will help you set up Telegram alerts for the Medical Data Monitor to receive notifications when failures are detected in your medical device data processing system.

## Prerequisites

- A Telegram account
- Access to the command line where you'll run the monitor

## Step 1: Create a Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** with BotFather by clicking "Start"
3. **Send the command** `/newbot`
4. **Follow the prompts**:
   - Enter a name for your bot (e.g., "Medical Data Monitor")
   - Enter a username for your bot (must end with 'bot', e.g., "medical_monitor_bot")
5. **Save the bot token** that BotFather gives you - it looks like this:
   ```
   1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

## Step 2: Get Your Chat ID

1. **Search for** `@userinfobot` in Telegram
2. **Start a chat** with this bot
3. **Send any message** to it (e.g., "Hello")
4. **Copy your Chat ID** from the response - it's a number like `123456789`

## Step 3: Configure Environment Variables

### Option A: Temporary Setup (Current Session Only)

Run these commands in your terminal:

```bash
export TELEGRAM_BOT_TOKEN='your_bot_token_here'
export TELEGRAM_CHAT_ID='your_chat_id_here'
```

### Option B: Permanent Setup

Add these lines to your shell profile file:

**For bash users** (edit `~/.bashrc`):
```bash
echo 'export TELEGRAM_BOT_TOKEN="your_bot_token_here"' >> ~/.bashrc
echo 'export TELEGRAM_CHAT_ID="your_chat_id_here"' >> ~/.bashrc
source ~/.bashrc
```

**For zsh users** (edit `~/.zshrc`):
```bash
echo 'export TELEGRAM_BOT_TOKEN="your_bot_token_here"' >> ~/.zshrc
echo 'export TELEGRAM_CHAT_ID="your_chat_id_here"' >> ~/.zshrc
source ~/.zshrc
```

## Step 4: Test Your Setup

1. **Start a chat** with your bot (search for the username you created)
2. **Send a message** to your bot (e.g., "Hello")
3. **Run the monitor** to test:
   ```bash
   ./start_medical_monitor.sh
   ```

You should receive a startup notification from your bot.

## Step 5: Configure Alert Settings (Optional)

You can customize the failure alert behavior:

```bash
# Alert after 3 failures in 5 minutes (default: 5 failures in 10 minutes)
export FAILURE_ALERT_THRESHOLD=3
export FAILURE_WINDOW_MINUTES=5
```

## Types of Alerts You'll Receive

### 🚨 Critical Failures (Immediate Alerts)
- **FHIR_R5_ERROR**: FHIR R5 processing failures
- **DATABASE_ERROR**: Database operation failures
- **PATIENT_NOT_FOUND**: Patient lookup failures
- **Container Failures**: Docker container crashes or unhealthy states

### ⚠️ Warning Alerts
- **High Failure Rate**: Multiple failures within the time window
- **Low Battery**: Kati Watch battery below 20%
- **Low Signal**: Kati Watch GSM signal below 50%
- **Command Failures**: AVA4 command execution failures

### ℹ️ Info Alerts
- **Monitor Start/Stop**: When the monitor starts or stops
- **Connection Issues**: MQTT connection problems

## Alert Message Format

Alerts include:
- **Emoji indicator** (🚨 for errors, ⚠️ for warnings, etc.)
- **Alert type** and description
- **Device information** (if applicable)
- **Error details** and relevant log lines
- **Timestamp** of when the alert was generated

## Troubleshooting

### Bot Not Responding
1. Make sure you've started a chat with your bot
2. Verify the bot token is correct
3. Check that the bot is not blocked

### No Alerts Received
1. Verify environment variables are set: `echo $TELEGRAM_BOT_TOKEN`
2. Check that the chat ID is correct
3. Ensure the monitor is running and connected to MQTT

### Too Many Alerts
1. Increase the failure threshold: `export FAILURE_ALERT_THRESHOLD=10`
2. Increase the time window: `export FAILURE_WINDOW_MINUTES=30`

## Security Notes

- **Keep your bot token secret** - don't share it publicly
- **The bot can only send messages** to you, not read your messages
- **You can block the bot** anytime if you want to stop alerts
- **Consider using a dedicated bot** for production monitoring

## Example Alert Messages

```
🚨 ERROR

Container Log Failure Detected

Container: stardust-kati-listener
Pattern: FHIR_R5_ERROR
Recent Logs:
```
Error processing FHIR R5 data: No module named 'app'
⚠️ FHIR R5 processing failed for patient 6825e82594d407871bd5851e
```

Please check the container immediately!

⏰ 2025-07-15 15:29:00
```

## Support

If you encounter issues:
1. Check the monitor logs for error messages
2. Verify your Telegram bot setup
3. Test with a simple message first
4. Ensure all environment variables are properly set 