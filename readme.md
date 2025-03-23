I'll enhance the header and make it more visually appealing by adding badges for marketplace.tf and Google Sheets:

# Update Sales Script

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Integration: marketplace.tf](https://img.shields.io/badge/Integration-marketplace.tf-orange.svg)](https://marketplace.tf)
[![Integration: Google Sheets](https://img.shields.io/badge/Integration-Google%20Sheets-green.svg)](https://sheets.google.com)

A Python script that updates sales data from a marketplace into a Google Sheets document. It connects to the Google Sheets API, processes sales data from a CSV file, and updates both the main worksheet and an unfiltered worksheet based on sales information. All prices are denominated in USD.

## Requirements

- A Google Sheets service account with access to the Google Sheets API
- A Google Sheet named **Master Spreadsheet** containing:

  - A worksheet named **TF2** (Main Sheet) with the following columns:

    | Type | Class | Quality | Item | Date Purchased | Paid (USD) | Date Sold | Sold (USD) | TTS (Days) | Profit (USD) | ROIC | ID  |
    | ---- | ----- | ------- | ---- | -------------- | ---------- | --------- | ---------- | ---------- | ------------ | ---- | --- |

  - A worksheet named **Unrecorded Sales** with the following columns:

    | Type | Class | Quality | Item | Date Sold | Price Sold | ID  |
    | ---- | ----- | ------- | ---- | --------- | ---------- | --- |

### Note on Autofilling

After copying the headers into Google Sheets, you can set up formulas for the corresponding categories:

- For profit: `=H2-F2`
- To convert USD price to keys, create a new column using the current key-USD price ratio

## Getting Started

### Setting Up Google Sheets API

1. **Create a Google Cloud Project**

   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project

2. **Enable the Google Sheets API**

   - In the Google Cloud Console, navigate to **APIs & Services > Library**
   - Search for "Google Sheets API" and enable it for your project

3. **Create a Service Account**

   - Navigate to **APIs & Services > Credentials**
   - Click on **Create Credentials** and select **Service Account**
   - Fill in the required details and click **Create**
   - On the next screen, you can skip granting this service account access to your project

4. **Create a JSON Key**

   - After creating the service account, click on it to open its details
   - Navigate to the **Keys** tab and click on **Add Key > Create New Key**
   - Choose **JSON** and click **Create**
   - This will download a `service_account.json` file to your computer

5. **Share Your Google Sheet**
   - Open your **Master Spreadsheet** in Google Sheets
   - Click on the **Share** button and share it with the service account email (found in the `service_account.json` file)

### Retrieving Marketplace Sales Data

1. Go to [marketplace.tf](https://marketplace.tf)
2. Navigate to the **Sales** tab
3. Click on **Download CSV**
4. Select the desired data ranges
5. **Important:** Ensure to select the **items** dropdown (otherwise the script will not work)

### Running the Script

1. Ensure you have Python installed on your machine
2. Install the required libraries:
   ```bash
   pip install requests gspread pandas
   ```
3. Place the `service_account.json` file in the same directory as the script
4. Ensure `itemschema.json` is updated
5. Run the script:
   ```bash
   python update-sales.py
   ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original script by Clone_Two (@clone_two) on Discord
- Modified slightly by me
