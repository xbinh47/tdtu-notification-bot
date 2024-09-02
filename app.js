const { Client, GatewayIntentBits, REST, Routes, SlashCommandBuilder, ActionRowBuilder, StringSelectMenuBuilder } = require('discord.js');
const { Builder, By, until } = require('selenium-webdriver');
const fs = require('fs').promises;
const cron = require('node-cron'); // Import the cron package
require('dotenv').config(); // Load environment variables

const chrome = require('selenium-webdriver/chrome');
const DISCORD_TOKEN = process.env.DISCORD_TOKEN;
const USER = process.env.USER;
const PASSWORD = process.env.PASSWORD;

const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent] });

client.on('ready', async () => {
    console.log(`Logged in as ${client.user.tag}!`);

    const commands = [
        new SlashCommandBuilder()
            .setName('notify')
            .setDescription('Notify new notifications from Student News'),
    ];

    const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

    try {
        console.log('Started refreshing application (/) commands.');

        await rest.put(
            Routes.applicationCommands(client.user.id),
            { body: commands.map(command => command.toJSON()) },
        );

        console.log('Successfully reloaded application (/) commands.');
    } catch (error) {
        console.error('Error while reloading application commands:', error);
    }
});

client.on('interactionCreate', async interaction => {
    if (interaction.isCommand() && interaction.commandName === 'notify') {
        const selectMenu = new StringSelectMenuBuilder()
            .setCustomId('select_menu')
            .setPlaceholder('Choose an option...')
            .addOptions([
                {
                    label: 'Information Technology',
                    description: 'Notification of Information Technology',
                    value: '5',
                },
            ]);

        const row = new ActionRowBuilder().addComponents(selectMenu);

        await interaction.reply({
            content: 'Please select an option from the menu:',
            components: [row],
            ephemeral: true // Optional: Make the initial response only visible to the user
        });
    }

    if (interaction.isStringSelectMenu() && interaction.customId === 'select_menu') {
        const selectedValue = interaction.values[0];

        // Immediately acknowledge the interaction to keep it alive
        await interaction.deferReply({ ephemeral: true });

        try {
            // Perform the longer task (fetching notifications)
            await fetchAndSendNotifications(interaction, selectedValue);

            // After the long task is done, update the original reply
            await interaction.editReply({ content: `Fetched notifications for selection: ${selectedValue}` });

            // Schedule daily notifications at 9:00 AM and 6:00 PM
            scheduleDailyNotifications(interaction, selectedValue);

        } catch (error) {
            console.error('Error fetching notifications:', error);
            await interaction.editReply({ content: 'There was an error fetching notifications.' });
        }
    }
});

client.login(DISCORD_TOKEN);

function scheduleDailyNotifications(interaction, MaDonVi) {
    // Schedule notification at 9:00 AM every day
    cron.schedule('0 9 * * *', async () => {
        console.log('Running scheduled task at 9:00 AM');
        try {
            await fetchAndSendNotifications(interaction, MaDonVi);
        } catch (error) {
            console.error('Error during scheduled task:', error);
        }
    });

    // Schedule notification at 6:00 PM every day
    cron.schedule('0 18 * * *', async () => {
        console.log('Running scheduled task at 6:00 PM');
        try {
            await fetchAndSendNotifications(interaction, MaDonVi);
        } catch (error) {
            console.error('Error during scheduled task:', error);
            await fs.appendFile('log.txt', `No new notification found at ${new Date().toLocaleString()}\n`, 'utf8');
        }
    });
}

async function fetchAndSendNotifications(interaction, MaDonVi) {
    const [newContents, newNotifications] = await getNotification(MaDonVi);

    if (newContents.length === 0) {
        await interaction.followUp({ content: 'No new notifications found.', ephemeral: true });
        return;
    }

    // Prepare embeds
    const embeds = newContents.map((title, index) => {
        const id = newNotifications[index];
        const url = `https://studentnews.tdtu.edu.vn/ThongBao/Detail/${id}`;

        return {
            title: `${index + 1}. ${title}`,
            url: url,
            color: 0x00AE86,
        };
    });

    // Split into chunks of 10
    const chunks = [];
    for (let i = 0; i < embeds.length; i += 10) {
        chunks.push(embeds.slice(i, i + 10));
    }

    // Ensure the first message is visible to everyone
    await interaction.followUp({ content: 'Here are the latest notifications:', ephemeral: false });

    // Send each chunk as a follow-up message
    for (const chunk of chunks) {
        await interaction.followUp({ embeds: chunk });
    }
}

async function getNotification(MaDonVi) {
    const options = new chrome.Options();
    options.addArguments('--ignore-certificate-errors', '--ignore-ssl-errors');

    let driver = await new Builder().forBrowser('chrome').setChromeOptions(options).build();
    let newContents = [];
    let newNotifications = [];

    try {
        await driver.get('https://stdportal.tdtu.edu.vn/');

        const txtUser = await driver.findElement(By.id('txtUser'));
        const txtPass = await driver.findElement(By.id('txtPass'));
        const btnLogin = await driver.findElement(By.id('btnLogIn'));

        await txtUser.sendKeys(USER);
        await txtPass.sendKeys(PASSWORD);
        await btnLogin.click();

        await driver.sleep(2000);

        await driver.get(`https://studentnews.tdtu.edu.vn/Home/Index`);
        await driver.get(`https://studentnews.tdtu.edu.vn/PhongBan/ThongBaoPhongBan?MaDonVi=${MaDonVi}`);

        const lstThongBaoDiv = await driver.wait(until.elementLocated(By.id('div_lstThongBao')), 10000);

        // Scroll to the bottom of the div to load all items
        let lastHeight = await driver.executeScript("return arguments[0].scrollHeight", lstThongBaoDiv);
        while (true) {
            await driver.executeScript("arguments[0].scrollTo(0, arguments[0].scrollHeight);", lstThongBaoDiv);
            await driver.sleep(1000); // Wait for the page to load

            let newHeight = await driver.executeScript("return arguments[0].scrollHeight", lstThongBaoDiv);
            if (newHeight === lastHeight) {
                break;
            }
            lastHeight = newHeight;
        }

        const listItems = await lstThongBaoDiv.findElements(By.className('list-item'));
        const readed_noti = await readFromFile('readed_noti.txt');

        for (let item of listItems) {
            const title = await item.findElement(By.css('.title')).getAttribute('title');
            const onclick = await item.findElement(By.css('.link-detail')).getAttribute('onclick');
            const idMatch = onclick.match(/Detail\/(\d+)/);
            const id = idMatch ? idMatch[1] : null;

            if (id && !readed_noti.includes(id)) {
                console.log(`Title: ${title}`);
                console.log(`ID: ${id}`);
                newNotifications.push(id);
                newContents.push(title);
            }
        }

        if (newNotifications.length > 0) {
            const updatedNotifications = [...readed_noti, ...newNotifications];
            await fs.writeFile('readed_noti.txt', updatedNotifications.join('\n'), 'utf8');
        }

    } finally {
        await driver.quit();
        return [newContents, newNotifications];
    }
}

async function readFromFile(filePath) {
    try {
        const data = await fs.readFile(filePath, 'utf8');
        return data.trim().split('\n').filter(Boolean);
    } catch (err) {
        if (err.code === 'ENOENT') {
            console.log(`File "${filePath}" does not exist. Creating a new one.`);
            await fs.writeFile(filePath, '', 'utf8');
            return [];
        } else {
            console.error('Error reading file:', err);
            throw err;
        }
    }
}
