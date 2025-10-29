const puppeteer = require('puppeteer');
const cheerio = require('cheerio');
const createCsvWriter = require('csv-writer').createObjectCsvWriter;
const fs = require('fs');
// Check if file exists
const fileExists = fs.existsSync('Scrapping/Scrappers/Data/pakistan_jobs.csv');

// Create CSV writer
const csvWriter = createCsvWriter({
    path: 'Scrapping/Scrappers/Data/pakistan_jobs.csv',
    header: [
        { id: 'City', title: 'City' },
        { id: 'Job_title', title: 'Job Title' },
        { id: 'Job_link', title: 'Job Link' },
        { id: 'Company_Name', title: 'Company Name' },
        { id: 'Company_link', title: 'Company Link' },
        { id: 'Location', title: 'Location' },
        { id: 'Salary', title: 'Salary' },
        { id: 'Job_Views', title: 'Job Views' },
        { id: 'Time_of_post', title: 'Time of Post' },
        { id: 'Job_Description', title: 'Job Description' },
        { id: 'Skills_Required', title: 'Skills Required' },
        { id: 'Job_Industry', title: 'Job Industry' },
        { id: 'Functional_Area', title: 'Functional Area' },
        { id: 'Total_positions', title: 'Total Positions' },
        { id: 'Job_Shift', title: 'Job Shift' },
        { id: 'Job_type', title: 'Job Type' },
        { id: 'Job_Location', title: 'Job Location' },
        { id: 'Gender', title: 'Gender' },
        { id: 'Minimum_Education', title: 'Minimum Education' },
        { id: 'Career_Level', title: 'Career Level' },
        { id: 'Minimum_Experience', title: 'Minimum Experience' },
        { id: 'Apply_Before', title: 'Apply Before' },
        { id: 'Posting_Date', title: 'Posting Date' }
    ],
    append: fileExists // append only if file already exists
});

// If the file doesn't exist, manually write the header row
if (!fileExists) {
    const headers = [
        'City','Job Title','Job Link','Company Name','Company Link','Location',
        'Salary','Job Views','Time of Post','Job Description','Skills Required',
        'Job Industry','Functional Area','Total Positions','Job Shift','Job Type',
        'Job Location','Gender','Minimum Education','Career Level',
        'Minimum Experience','Apply Before','Posting Date'
    ];
    fs.writeFileSync('Scrapping/Scrappers/Data/pakistan_jobs.csv' , headers.join(',') + '\n', 'utf8');
}

// City configuration
const cities = [
    { name: 'Islamabad', url: 'https://www.rozee.pk/job/jsearch/q/all/fc/1180/stype/title' },
    { name: 'Karachi', url: 'https://www.rozee.pk/job/jsearch/q/all/fc/1184/stype/title' },
    { name: 'Lahore', url: 'https://www.rozee.pk/job/jsearch/q/all/fc/1185/stype/title' },
    { name: 'Rawalpindi', url: 'https://www.rozee.pk/job/jsearch/q/all/fc/1190/stype/title' }
];

async function scrapeJobDetails(tab, link, cityName) {
    try {
        await tab.goto(link, { waitUntil: 'domcontentloaded', timeout: 30000 });

        const content = await tab.content();
        const $ = cheerio.load(content);

        const jobInfo = {
            City: cityName,
            Job_title: $('h1.jtitle.font24.text-dark > bdi').text().trim() || 'Null',
            Job_link: link,
            Company_Name: $('h2.cname a bdi').text().trim() || 'Null',
            Company_link: $('h2.cname a').attr('href') || 'Null',
            Location: $('h4.lh1.cname').text().split(',')[0].trim() || 'Null',
            Salary: $('div.mrsl.mt10.ofa.font18.text-right.text-dark.d-flex.align-items-center').text().trim() || 'N/A',
            Job_Views: $('span.font16.mr-3.d-flex.align-items-center span').last().text().trim() || 'Null',
            Time_of_post: $('span.font16 span').first().text().trim().split('views')[0].trim() || 'Null',
            Job_Description: $('#jbDetail .jblk ul18 p').map(function () { return $(this).text().trim(); }).get().join(' ') || 'Null',
            Skills_Required: $('div.jblk h4:contains("Skills") + div.jcnt a').map((_, el) => $(el).text().trim()).get().join(', ') || "Null",
            Job_Industry: $('b:contains("Industry:")').closest('.row').find('.jblk').text().trim() || 'N/A',
            Functional_Area: $('b:contains("Functional Area:")').closest('.row').find('.jblk').text().trim() || 'N/A',
            Total_positions: $('b:contains("Total Positions:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Job_Shift: $('b:contains("Job Shift:")').closest('.row').find('bdi').text().trim() || 'N/A',
            Job_type: $('b:contains("Job Type:")').closest('.row').find('.jblk').map((i, el) => $(el).text().trim()).get().join('/') || 'N/A',
            Job_Location: $('b:contains("Job Location:")').closest('.row').find('.jblk span').map((i, el) => $(el).text().trim()).get().join(', ') || 'N/A',
            Gender: $('b:contains("Gender:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Minimum_Education: $('b:contains("Minimum Education:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Career_Level: $('b:contains("Career Level:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Minimum_Experience: $('b:contains("Minimum Experience:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Apply_Before: $('b:contains("Apply Before:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
            Posting_Date: $('b:contains("Posting Date:")').closest('.row').find('div.col-lg-7').text().trim() || 'N/A',
        };

        return jobInfo;
    } catch (error) {
        console.error(`Error scraping job at ${link}:`, error.message);
        return null;
    }
}

async function scrapeCityJobs(browser, cityName, cityUrl, maxJobs = 20) {
    console.log(`\n========================================`);
    console.log(`Starting to scrape jobs for ${cityName}`);
    console.log(`========================================\n`);

    const mainPage = await browser.newPage();
    await mainPage.goto(cityUrl, { waitUntil: 'domcontentloaded' });

    const maxConcurrentTabs = 3;
    let jobsScraped = 0;
    let currentPage = 0;

    while (jobsScraped < maxJobs) {
        try {
            await mainPage.waitForSelector('h3.s-18 a', { timeout: 10000 });
            currentPage++;
            console.log(`[${cityName}] Scraping page ${currentPage}...`);

            // Extract all job links from the current page
            let jobLinks = await mainPage.$$eval('h3.s-18 a', (anchors) => anchors.map(a => a.href));
            console.log(`[${cityName}] Found ${jobLinks.length} job links on page ${currentPage}.`);

            // Only take the number of jobs needed to reach maxJobs
            const jobsNeeded = maxJobs - jobsScraped;
            jobLinks = jobLinks.slice(0, jobsNeeded);

            // Process jobs in batches
            while (jobLinks.length > 0) {
                const batchLinks = jobLinks.splice(0, maxConcurrentTabs);
                const tabs = await Promise.all(batchLinks.map(() => browser.newPage()));

                const results = await Promise.all(
                    batchLinks.map(async (link, index) => {
                        const tab = tabs[index];
                        const jobInfo = await scrapeJobDetails(tab, link, cityName);
                        await tab.close();
                        return jobInfo;
                    })
                );

                // Filter out null results and write to CSV
                const validJobs = results.filter(job => job !== null);
                if (validJobs.length > 0) {
                    await csvWriter.writeRecords(validJobs);
                    jobsScraped += validJobs.length;
                    console.log(`[${cityName}] Progress: ${jobsScraped}/${maxJobs} jobs scraped`);
                }
            }

            // Check if we've reached the target
            if (jobsScraped >= maxJobs) {
                console.log(`[${cityName}] Reached target of ${maxJobs} jobs!`);
                break;
            }

            // Check if there's a next page
            const hasNextPage = await mainPage.$('a.next');
            if (hasNextPage) {
                console.log(`[${cityName}] Moving to the next page...`);
                await Promise.all([
                    mainPage.click('a.next'),
                    mainPage.waitForNavigation({ waitUntil: 'domcontentloaded' }),
                ]);
            } else {
                console.log(`[${cityName}] No more pages available. Scraped ${jobsScraped} jobs.`);
                break;
            }
        } catch (error) {
            console.error(`[${cityName}] Error on page ${currentPage}:`, error.message);
            break;
        }
    }

    await mainPage.close();
    console.log(`\n[${cityName}] Completed! Total jobs scraped: ${jobsScraped}\n`);
}

(async () => {
    const startTime = Date.now();
    console.log('Starting multi-city job scraper...\n');

    const browser = await puppeteer.launch({ headless: true });

    try {
        for (const city of cities) {
            await scrapeCityJobs(browser, city.name, city.url, 50);
        }

        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000 / 60).toFixed(2);

        console.log('\n========================================');
        console.log('SCRAPING COMPLETED!');
        console.log(`Total time: ${duration} minutes`);
        console.log('Data saved to: Scrappers/Data/pakistan_jobs.csv');
        console.log('========================================\n');

    } catch (error) {
        console.error('Fatal error:', error);
    } finally {
        await browser.close();
    }
})();