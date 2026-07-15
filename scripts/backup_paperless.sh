# ==========================================
# PAPERLESS-NGX BACKUP SCRIPT
# Mirror with 90-Day Trash Retention
# ==========================================

# --- CONFIGURATION ---
CONTAINER_NAME="paperless-webserver-1"
EXPORT_DIR="/mnt/storage/paperless_storage/export" 
NAS_DIR="/mnt/WumbologyNAS/6. Network Backup/Paperless Backup"
CLOUD_BASE="gdrive-crypt:"
CLOUD_DEST="$CLOUD_BASE/PaperlessBackup"
LOG_FILE="/var/log/paperless_backup.log"
USER_CONFIG="/home/dietpi/.config/rclone/rclone.conf"

# Retention Policy (Days to keep in Trash before permanent deletion)
DAYS_TO_KEEP=90

# --- DYNAMIC VARIABLES ---
DATE=$(date +%Y-%m-%d_%H-%M)

# Trash Locations
NAS_TRASH_BASE="/mnt/WumbologyNAS/6. Network Backup/Paperless Trash"
NAS_TRASH="$NAS_TRASH_BASE/$DATE"

CLOUD_TRASH_BASE="$CLOUD_BASE/PaperlessTrash"
CLOUD_TRASH="$CLOUD_TRASH_BASE/$DATE"

# --- LOGGING SETUP ---
if [ ! -f "$LOG_FILE" ]; then
    sudo touch "$LOG_FILE"
fi
sudo chmod 666 "$LOG_FILE"

echo "---------------------------------" >> "$LOG_FILE"
echo "Starting Backup: $(date)" >> "$LOG_FILE"

# ==========================================
# STEP 1: EXPORT DATA & CONFIGS
# ==========================================
echo "Step 1: Exporting data and configs..." >> "$LOG_FILE"

# Backup docker-compose and .env (Adjust '/opt/paperless' if yours is elsewhere)
#sudo cp /opt/paperless/docker-compose.yml "$EXPORT_DIR/" 2>/dev/null
#sudo cp /opt/paperless/.env "$EXPORT_DIR/" 2>/dev/null

# Export the database and documents
if sudo docker exec "$CONTAINER_NAME" document_exporter ../export -na -d >> "$LOG_FILE" 2>&1; then
    echo "Export successful." >> "$LOG_FILE"
else
    echo "CRITICAL: Export failed! Halting script to protect backups." >> "$LOG_FILE"
    exit 1
fi

# ==========================================
# STEP 2: NAS SYNC (With Safety Net)
# ==========================================
echo "Step 2: Syncing to NAS..." >> "$LOG_FILE"
sudo mkdir -p "$NAS_DIR"
sudo mkdir -p "$NAS_TRASH_BASE"

# --backup and --backup-dir move deleted/changed files to the Trash folder
sudo rsync -avh --delete --backup --backup-dir="$NAS_TRASH" "$EXPORT_DIR/" "$NAS_DIR/" >> "$LOG_FILE" 2>&1

# ==========================================
# STEP 3: CLOUD SYNC (With Safety Net)
# ==========================================
echo "Step 3: Syncing to Google Drive..." >> "$LOG_FILE"

# --backup-dir moves deleted/changed files to the encrypted Trash folder
sudo rclone sync "$EXPORT_DIR" "$CLOUD_DEST" --backup-dir "$CLOUD_TRASH" --config "$USER_CONFIG" --progress >> "$LOG_FILE" 2>&1

# ==========================================
# STEP 4: GARBAGE COLLECTION (90 Days)
# ==========================================
echo "Step 4: Cleaning up Trash older than $DAYS_TO_KEEP days..." >> "$LOG_FILE"

# 4a. Clean NAS Trash
# Finds directories inside the base trash folder older than 90 days and removes them
# Ensure the base trash folder exists so 'find' doesn't complain
sudo mkdir -p "$NAS_TRASH_BASE"
sudo find "$NAS_TRASH_BASE" -mindepth 1 -maxdepth 1 -type d -mtime +$DAYS_TO_KEEP -exec rm -rf {} + >> "$LOG_FILE" 2>&1

# 4b. Clean Cloud Trash
# Tell rclone to create the base Trash folder if it doesn't exist yet
sudo rclone mkdir "$CLOUD_TRASH_BASE" --config "$USER_CONFIG" >> "$LOG_FILE" 2>&1

# Delete files older than 90 days, then remove any empty directories left behind
sudo rclone delete "$CLOUD_TRASH_BASE" --min-age ${DAYS_TO_KEEP}d --config "$USER_CONFIG" >> "$LOG_FILE" 2>&1
sudo rclone rmdirs "$CLOUD_TRASH_BASE" --leave-root --config "$USER_CONFIG" >> "$LOG_FILE" 2>&1

echo "Backup Complete: $(date)" >> "$LOG_FILE"
