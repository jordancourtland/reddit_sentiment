# Deployment Guide: Upload Databases to Render (Free Tier)

## Option 1: Cloud Storage + Environment Variables (Recommended)

### Step 1: Upload Both Databases to Google Drive

1. **Go to [Google Drive](https://drive.google.com)**
2. **Upload both files:**
   - `analysis.db` (11MB)
   - `reddit.db` (116MB)
3. **For each file, right-click** → "Get link"
4. **Copy both links** (format: `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`)

### Step 2: Convert to Direct Download URLs

Replace the Google Drive URL format for each file:
- **From:** `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
- **To:** `https://drive.google.com/uc?export=download&id=FILE_ID`

### Step 3: Set Environment Variables in Render

In your Render dashboard, add these environment variables:

```
ANALYSIS_DB_URL=https://drive.google.com/uc?export=download&id=ANALYSIS_FILE_ID
REDDIT_DB_URL=https://drive.google.com/uc?export=download&id=REDDIT_FILE_ID
```

### Step 4: Deploy

The app will automatically download both database files on startup.

## Option 2: Render File Upload (Alternative)

1. **Go to your Render dashboard**
2. **Click on your web service**
3. **Go to "Files" tab** (if available)
4. **Upload both files:**
   - `analysis.db` (11MB)
   - `reddit.db` (116MB)

## Verification

After deployment, check your app logs to see:
- ✅ reddit.db downloaded successfully
- ✅ analysis.db downloaded successfully
- ✅ Both databases are valid

## Troubleshooting

**If databases don't download:**
- Check both environment variables (REDDIT_DB_URL and ANALYSIS_DB_URL)
- Verify Google Drive links are public
- Check Render logs for download errors

**If app crashes:**
- Ensure both database files are valid SQLite files
- Check file permissions on Render
- Verify database schema matches your app expectations

## Notes

- This approach keeps you on Render's free tier
- Downloads both databases (127MB total)
- Databases will be re-downloaded after each container restart
- Perfect for testing and development 