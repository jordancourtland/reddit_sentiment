# Deployment Guide: Upload Local Data to Render

## Option 1: Render File Upload (Recommended)

1. **Go to your Render dashboard**
2. **Click on your web service**
3. **Go to "Files" tab** (if available)
4. **Upload your database files:**
   - `analysis.db` (11MB)
   - `reddit.db` (116MB)

## Option 2: Cloud Storage + Environment Variables

### Step 1: Upload to Cloud Storage

**Google Drive:**
1. Upload `analysis.db` and `reddit.db` to Google Drive
2. Right-click each file → "Get link"
3. Replace the URL format: `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
4. Convert to direct download: `https://drive.google.com/uc?export=download&id=FILE_ID`

**Dropbox:**
1. Upload files to Dropbox
2. Right-click → "Copy link"
3. Replace `www.dropbox.com` with `dl.dropboxusercontent.com`
4. Remove `?dl=0` and add `?dl=1`

### Step 2: Set Environment Variables in Render

In your Render dashboard, add these environment variables:

```
REDDIT_DB_URL=https://your-direct-download-url-for-reddit.db
ANALYSIS_DB_URL=https://your-direct-download-url-for-analysis.db
```

### Step 3: Deploy

The app will automatically download the database files on startup.

## Option 3: Git Repository (Small files only)

For `analysis.db` only (11MB is manageable):

1. **Add to git:**
   ```bash
   git add analysis.db
   git commit -m "Add analysis database"
   git push
   ```

2. **Update .gitignore to exclude reddit.db:**
   ```
   reddit.db
   ```

## Verification

After deployment, check your app logs to see:
- ✅ Database files downloaded successfully
- ✅ Database files are valid

## Troubleshooting

**If databases don't download:**
- Check environment variable URLs
- Verify cloud storage links are public
- Check Render logs for download errors

**If app crashes:**
- Ensure database files are valid SQLite files
- Check file permissions on Render
- Verify database schema matches your app expectations 