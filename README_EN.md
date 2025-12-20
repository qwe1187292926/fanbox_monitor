# Fanbox Creator Update Monitor (Python Version)

## Overview

- **Monitoring Targets**: 
  - Creators you are **supporting** on Fanbox (enabled by default)
  - Creators you are **following** (optional, enabled via configuration)
- **Implementation**: 
  - Calls `post.listSupporting` API to detect updates from supported creators
  - If following detection is enabled, calls `creator.listFollowing` to get the following list, then calls `post.listCreator` for each creator to detect updates
  - Compares the latest post `id` for each creator, outputs "new post" notifications and sends Bark notifications when changes are detected
- **Authentication**: Uses browser login cookies (consistent with the browser extension in this repository, relies on cookie authentication).


**Work is hard! If you love this project, please consider star me~**

---

## Installation

Install dependencies in the repository root directory:

```bash
pip install -r fanbox_monitor/requirements.txt
```

(Or you can just install `requests` and `onepush`: `pip install requests onepush`)

---

## Configuration

### 1. Get Cookie

1. Log in to `https://www.pixiv.net/fanbox/supporting` and ensure you can see the "Supporting" page.
2. Open browser Developer Tools → Network panel.
3. Refresh the page, find a `post.listSupporting` or other fanbox API request.
4. In the request's **Request Headers**, find `Cookie` and copy the entire value.
5. Create `fanbox_monitor_config.json` in the repository root directory with the following content:

```json
{
  "cookie": "Paste your entire Cookie string here",
  "limit": 50,
  "state_file": "fanbox_monitor_state.json",
  "bark_key": "Your Bark push key (optional, for mobile notifications)",
  "bark_group": "Optional Bark group name, default: Fanbox Update Monitor",
  "check_following": false,
  "min_fee_required": 0,
  "creators_file": "fanbox_monitor_creators.json",
  "proxy": "http://172.17.0.1:7890"
}
```

### Configuration Fields

- **limit**: Number of posts to fetch from "Supporting" list or individual creators each time, default 50 is fine.
- **state_file**: Local JSON file to save "latest post id for each creator". The state file distinguishes between supporting and following types.
- **bark_key**: If provided, will send Bark notifications via onepush when new posts are detected. Notifications will use the creator's avatar as the icon.
- **bark_group**: Bark group name for categorizing notifications in the Bark client. If not set, uses default value `Fanbox Update Monitor`.
- **check_following**: Whether to also detect creators you are following (not just supporting). When set to `true`, will fetch your following list and detect new posts from each followed creator. Default `false`.
- **min_fee_required**: Default minimum fee amount (JPY). When a creator doesn't have a separate configuration, this value is used as the default. Set to `0` to disable restriction (all posts will be notified).
- **creators_file**: Filename to save the list of supporting and followed creators. The script will automatically update this file after each detection, containing IDs, names, and avatar URLs of all supporting and followed creators.
- **proxy**: HTTP proxy address (optional). If you need to access Fanbox API through a proxy, set this field, e.g., `"http://172.17.0.1:7890"`. If not set, no proxy will be used.

### Per-Creator Minimum Fee Configuration

The script automatically detects all supporting and followed creators and creates minimum fee configurations for each creator in the config file. You only need to modify the `creator_min_fees` field in the config file:

```json
{
  "cookie": "Your Cookie",
  "limit": 50,
  "state_file": "fanbox_monitor_state.json",
  "bark_key": "Your Bark key",
  "bark_group": "Fanbox Update Monitor",
  "check_following": true,
  "min_fee_required": 0,
  "creators_file": "fanbox_monitor_creators.json",
  "proxy": "http://172.17.0.1:7890",
  "creator_min_fees": {
    "creator_id_1": 500,
    "creator_id_2": 0,
    "creator_id_3": 1000
  }
}
```

- **creator_min_fees**: Minimum fee configuration for each creator (key is creator ID, value is minimum amount in JPY)
  - The script will automatically add creators to the config file when first detected, with default value `0` (no restriction)
  - You only need to modify the value for the corresponding creator ID
  - If a creator is not in this configuration, `min_fee_required` will be used as the default
  - **Note**: You don't need to manually find creator IDs. The script will automatically detect and write them to the config file. You only need to modify the values.

---

## Usage

Run in the repository root directory (or copy the entire `fanbox_monitor` folder separately and run inside it):

```bash
cd fanbox_monitor
python monitor.py
```

The script executes **one detection** per run, suitable for periodic calls by external schedulers (scheduled tasks / cron, etc.):

- When a creator has a new post:
  - Prints in terminal: `[NEW] Supporting/Following - Creator Name (ID) has new post: Title (id=xxx, published at time)`
  - If `bark_key` is configured, will simultaneously send Bark notification to your phone:
    - **Supporting creators**: Title is `Creator Name you support has an update!`
    - **Following creators**: Title is `Creator Name you follow has an update!`
    - Notifications will use the creator's avatar as the icon
    - Clicking the notification opens the corresponding Fanbox post page

- The state file distinguishes between supporting and following types, using `supporting:creator_id` and `following:creator_id` as keys.

- On subsequent runs, reads the latest post id for each creator from `state_file`, only notifying about **new posts after that**.

- Each creator can have a separate minimum fee configuration (in the `creator_min_fees` field of the config file). The script will automatically add creators to the config file when first detected, with default value `0` (no restriction). You only need to modify the value for the corresponding creator ID. If a creator doesn't have a separate configuration, `min_fee_required` will be used as the default.

- After each detection, the script automatically saves the list of supporting and followed creators to the file specified in `creators_file`, making it easy to view all creators you are monitoring.

- If an error occurs during runtime and `bark_key` is configured, an error notification will be sent to your phone.

---

## Language Support

The script supports multiple languages. The default language is determined by your system locale. You can also manually set the language in the configuration file:

```json
{
  "language": "en"
}
```

Supported languages:
- `en` - English
- `zh` - Chinese (Simplified)
- `zh-tw` - Chinese (Traditional)
- `ja` - Japanese
- `ko` - Korean

---

## Error Handling

If an error occurs during script execution (network connection failure, API request failure, parsing error, etc.), and `bark_key` is configured, an error notification will automatically be sent to your phone:

- Title: `Fanbox Monitor Runtime Error`
- Content: Specific error message (e.g., `Detection error: HTTP error 403 Forbidden`)
- Group: Uses configured `bark_group` (default: `Fanbox Update Monitor`)

**Note**: Error notifications are only sent if `bark_key` is configured. If `bark_key` is not configured, error messages will only be printed to the terminal.

