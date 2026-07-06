const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

async function generatePdf() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.error('Usage: node generate_pdf.js <input.html> <output.pdf>');
        process.exit(1);
    }
    
    const inputPath = args[0];
    const outputPath = args[1];
    
    if (!fs.existsSync(inputPath)) {
        console.error(`Input file not found: ${inputPath}`);
        process.exit(1);
    }
    
    try {
        const browser = await puppeteer.launch({
            headless: "new",
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        
        const page = await browser.newPage();
        
        // Construct file:// URL for absolute path handling
        const fileUrl = `file://${path.resolve(inputPath)}`;
        
        // Wait until network is idle so CDN scripts (like Tailwind) can load
        await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 30000 });
        
        await page.pdf({
            path: outputPath,
            format: 'A4',
            printBackground: true, // Required for CSS backgrounds to show up
            margin: {
                top: '20px',
                right: '20px',
                bottom: '20px',
                left: '20px'
            }
        });
        
        await browser.close();
        console.log(`Successfully generated PDF: ${outputPath}`);
    } catch (err) {
        console.error('Error generating PDF:', err);
        process.exit(1);
    }
}

generatePdf();
