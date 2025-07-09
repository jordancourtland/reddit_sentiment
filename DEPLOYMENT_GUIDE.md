# Deployment Guide: Upload analysis.db to Render (Free Tier)

## Option 1: Cloud Storage + Environment Variables (Recommended)

### Step 1: Upload analysis.db to Google Drive

1. **Go to [Google Drive](https://drive.google.com)**
2. **Upload `analysis.db`** from your local machine
3. **Right-click the file** → "Get link"
4. **Copy the link** (format: `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`)

### Step 2: Convert to Direct Download URL

Replace the Google Drive URL format:
- **From:** `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
- **To:** `https://drive.google.com/uc?export=download&id=FILE_ID`

### Step 3: Set Environment Variable in Render

In your Render dashboard, add this environment variable:

```
ANALYSIS_DB_URL=https://drive.google.com/uc?export=download&id=YOUR_FILE_ID
```

### Step 4: Deploy

The app will automatically download `analysis.db` on startup.

## Option 2: Render File Upload (Alternative)

1. **Go to your Render dashboard**
2. **Click on your web service**
3. **Go to "Files" tab** (if available)
4. **Upload `analysis.db`** (11MB)

## Verification

After deployment, check your app logs to see:
- ✅ analysis.db downloaded successfully
- ✅ analysis.db is valid

## Troubleshooting

**If database doesn't download:**
- Check the ANALYSIS_DB_URL environment variable
- Verify Google Drive link is public
- Check Render logs for download errors

**If app crashes:**
- Ensure analysis.db is a valid SQLite file
- Check file permissions on Render
- Verify database schema matches your app expectations

## Notes

- This approach keeps you on Render's free tier
- Only downloads analysis.db (11MB) - much more manageable
- Database will be re-downloaded after each container restart
- Perfect for testing and development 