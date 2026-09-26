<?php
declare(strict_types=1);

function env_value(string $name, string $default = ''): string
{
    $value = getenv($name);
    return $value === false ? $default : (string) $value;
}

function db(string $database): PDO
{
    $host = env_value('DB_HOST', 'ac-database');
    $port = env_value('DB_PORT', '3306');
    $user = env_value('DB_USER', 'root');
    $password = env_value('DB_PASSWORD', 'password');

    return new PDO(
        "mysql:host={$host};port={$port};dbname={$database};charset=utf8mb4",
        $user,
        $password,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_TIMEOUT => 3,
        ]
    );
}

function scalar(?PDO $pdo, string $sql, mixed $default = 0): mixed
{
    if ($pdo === null) {
        return $default;
    }

    try {
        $value = $pdo->query($sql)->fetchColumn();
        return $value === false || $value === null ? $default : $value;
    } catch (Throwable) {
        return $default;
    }
}

function rows(?PDO $pdo, string $sql): array
{
    if ($pdo === null) {
        return [];
    }

    try {
        return $pdo->query($sql)->fetchAll();
    } catch (Throwable) {
        return [];
    }
}

function connection(string $database, array &$errors): ?PDO
{
    try {
        return db($database);
    } catch (Throwable $error) {
        $errors[] = "{$database}: {$error->getMessage()}";
        return null;
    }
}

function yes_no(string $value): string
{
    return in_array(strtolower($value), ['1', 'true', 'yes', 'on'], true) ? 'On' : 'Off';
}

function duration_text(int $seconds): string
{
    if ($seconds <= 0) {
        return 'Unknown';
    }

    $days = intdiv($seconds, 86400);
    $seconds %= 86400;
    $hours = intdiv($seconds, 3600);
    $seconds %= 3600;
    $minutes = intdiv($seconds, 60);

    $parts = [];
    if ($days > 0) {
        $parts[] = "{$days}d";
    }
    if ($hours > 0) {
        $parts[] = "{$hours}h";
    }
    $parts[] = "{$minutes}m";

    return implode(' ', $parts);
}

function class_name(int $class): string
{
    return [
        1 => 'Warrior',
        2 => 'Paladin',
        3 => 'Hunter',
        4 => 'Rogue',
        5 => 'Priest',
        6 => 'Death Knight',
        7 => 'Shaman',
        8 => 'Mage',
        9 => 'Warlock',
        11 => 'Druid',
    ][$class] ?? "Class {$class}";
}

function race_faction(int $race): string
{
    return in_array($race, [1, 3, 4, 7, 11], true) ? 'Alliance' : 'Horde';
}

$errors = [];
$auth = connection(env_value('AUTH_DB', 'acore_auth'), $errors);
$characters = connection(env_value('CHARACTERS_DB', 'acore_characters'), $errors);

$onlineCharacters = (int) scalar($characters, 'SELECT COUNT(*) FROM characters WHERE online = 1');
$totalCharacters = (int) scalar($characters, 'SELECT COUNT(*) FROM characters');
$latestUptime = rows($auth, 'SELECT uptime, maxplayers, starttime, revision FROM uptime ORDER BY starttime DESC LIMIT 1');
$uptime = $latestUptime[0] ?? [];
$initialUsers = rows($auth, "SELECT username, last_ip, last_login, online FROM account WHERE username IN ('GEORGE','HARPER','COLBY','ISAAC') ORDER BY username");
$recentCharacters = rows(
    $characters,
    'SELECT name, level, race, class, online, zone, map, money, totaltime FROM characters ORDER BY online DESC, totaltime DESC LIMIT 12'
);
$classBreakdown = rows($characters, 'SELECT class, COUNT(*) AS total FROM characters GROUP BY class ORDER BY total DESC');

$factionCounts = ['Alliance' => 0, 'Horde' => 0];
foreach (rows($characters, 'SELECT race, COUNT(*) AS total FROM characters GROUP BY race') as $row) {
    $factionCounts[race_faction((int) $row['race'])] += (int) $row['total'];
}

$botAccountCount = (int) scalar(
    $auth,
    "SELECT COUNT(*) FROM account WHERE username LIKE 'RNDBOT%' OR username LIKE 'BOT%' OR username LIKE 'PLAYERBOT%'",
    0
);

$cards = [
    ['label' => 'Characters online', 'value' => $onlineCharacters, 'hint' => "{$totalCharacters} total characters"],
    ['label' => 'Accounts', 'value' => scalar($auth, 'SELECT COUNT(*) FROM account'), 'hint' => scalar($auth, 'SELECT COUNT(*) FROM account WHERE online = 1') . ' account sessions online'],
    ['label' => 'Configured bots', 'value' => env_value('CONFIGURED_BOTS_MIN', '1500') . '–' . env_value('CONFIGURED_BOTS_MAX', '1500'), 'hint' => "{$botAccountCount} bot-like accounts currently found"],
    ['label' => 'Auction listings', 'value' => scalar($characters, 'SELECT COUNT(*) FROM auctionhouse'), 'hint' => scalar($characters, 'SELECT COUNT(DISTINCT itemguid) FROM auctionhouse') . ' item GUIDs'],
    ['label' => 'Guilds', 'value' => scalar($characters, 'SELECT COUNT(*) FROM guild'), 'hint' => scalar($characters, 'SELECT COUNT(*) FROM guild_member') . ' guild members'],
    ['label' => 'World uptime', 'value' => duration_text((int) ($uptime['uptime'] ?? 0)), 'hint' => isset($uptime['maxplayers']) ? "Peak {$uptime['maxplayers']} players" : 'Waiting for uptime row'],
];

$serverInfo = [
    'Dashboard' => 'http://127.0.0.1:' . env_value('DASHBOARD_EXTERNAL_PORT', '3000'),
    'Realmlist host' => env_value('REALMLIST_HOST', '127.0.0.1'),
    'Auth port' => env_value('AUTH_PORT', '3724'),
    'World port' => env_value('WORLD_PORT', '8085'),
    'SOAP port' => env_value('SOAP_PORT', '7878'),
    'Refresh' => env_value('DASHBOARD_REFRESH_SECONDS', '15') . ' seconds',
    'Core revision' => $uptime['revision'] ?? 'Unknown until worldserver starts',
];

$moduleInfo = [
    'mod-playerbots' => 'Bots ' . env_value('CONFIGURED_BOTS_MIN', '1500') . '–' . env_value('CONFIGURED_BOTS_MAX', '1500'),
    'Solo LFG bots' => yes_no(env_value('CONFIGURED_LFG_BOTS', '1')),
    'Battleground bots' => yes_no(env_value('CONFIGURED_BG_BOTS', '1')) . ' / autojoin ' . yes_no(env_value('CONFIGURED_BG_AUTOJOIN', '1')),
    'mod-autobalance' => yes_no(env_value('CONFIGURED_AUTOBALANCE', '1')),
    'mod-aoe-loot' => yes_no(env_value('CONFIGURED_AOE_LOOT', '1')) . ' / range ' . env_value('CONFIGURED_AOE_LOOT_RANGE', '55.0'),
    'DungeonRespawn' => yes_no(env_value('CONFIGURED_DUNGEON_RESPAWN', '1')),
    'mod-npc-all-mounts' => yes_no(env_value('CONFIGURED_ALL_MOUNTS_NPC', '1')),
    'mod-money-for-kills' => yes_no(env_value('CONFIGURED_MONEY_FOR_KILLS', '1')) . ' / PvP corpse loot ' . env_value('CONFIGURED_MFK_PVP_LOOT', '0') . '%',
    'mod-ah-bot-plus' => 'seller ' . yes_no(env_value('CONFIGURED_AHBOT_SELLER', '1')) . ' / buyer ' . yes_no(env_value('CONFIGURED_AHBOT_BUYER', '1')),
];

if (($_GET['format'] ?? '') === 'json') {
    header('Content-Type: application/json');
    echo json_encode([
        'generated_at' => gmdate('c'),
        'errors' => $errors,
        'cards' => $cards,
        'server' => $serverInfo,
        'modules' => $moduleInfo,
        'factions' => $factionCounts,
        'classes' => $classBreakdown,
        'initial_users' => $initialUsers,
        'recent_characters' => $recentCharacters,
    ], JSON_PRETTY_PRINT);
    exit;
}

$refresh = max(5, (int) env_value('DASHBOARD_REFRESH_SECONDS', '15'));
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= htmlspecialchars(env_value('DASHBOARD_TITLE', 'AzerothCore Local Observer'), ENT_QUOTES) ?></title>
    <style>
        :root { color-scheme: dark; --bg: #0d1117; --panel: #151b23; --muted: #8b949e; --text: #e6edf3; --accent: #f0b35b; --ok: #3fb950; --bad: #f85149; --line: #30363d; }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, Segoe UI, Arial, sans-serif; background: radial-gradient(circle at top left, #1f2a44 0, transparent 32rem), var(--bg); color: var(--text); }
        main { width: min(1180px, calc(100% - 32px)); margin: 0 auto; padding: 32px 0 48px; }
        header { display: flex; justify-content: space-between; gap: 16px; align-items: end; margin-bottom: 24px; }
        h1, h2 { margin: 0; }
        h1 { font-size: clamp(28px, 4vw, 46px); letter-spacing: -0.04em; }
        h2 { font-size: 18px; margin-bottom: 12px; color: #fff; }
        .muted { color: var(--muted); }
        .pill { border: 1px solid var(--line); background: rgba(255,255,255,.04); padding: 8px 12px; border-radius: 999px; white-space: nowrap; }
        .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 16px; }
        .card, section { background: color-mix(in oklab, var(--panel), transparent 5%); border: 1px solid var(--line); border-radius: 18px; padding: 18px; box-shadow: 0 18px 60px rgba(0,0,0,.25); }
        .card { grid-column: span 4; }
        .card .label { color: var(--muted); font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }
        .card .value { font-size: 34px; font-weight: 800; margin: 8px 0 4px; color: #fff; }
        .wide { grid-column: span 8; }
        .half { grid-column: span 6; }
        .full { grid-column: 1 / -1; }
        dl { display: grid; grid-template-columns: 190px 1fr; gap: 10px 16px; margin: 0; }
        dt { color: var(--muted); }
        dd { margin: 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); }
        th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
        tr:last-child td { border-bottom: 0; }
        .status-on { color: var(--ok); font-weight: 700; }
        .status-off { color: var(--bad); font-weight: 700; }
        .bar { height: 10px; border-radius: 999px; background: #222b36; overflow: hidden; }
        .bar span { display: block; height: 100%; background: linear-gradient(90deg, var(--accent), #f778ba); }
        .errors { border-color: color-mix(in oklab, var(--bad), var(--line)); background: rgba(248,81,73,.08); }
        a { color: var(--accent); }
        @media (max-width: 860px) { .card, .wide, .half { grid-column: 1 / -1; } header { align-items: start; flex-direction: column; } dl { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
<main>
    <header>
        <div>
            <h1><?= htmlspecialchars(env_value('DASHBOARD_TITLE', 'AzerothCore Local Observer'), ENT_QUOTES) ?></h1>
            <div class="muted">Local controls, live monitoring, and character statistics.</div>
        </div>
        <div class="pill"><a href="http://127.0.0.1:8765/">Standalone controls</a> · <a href="?format=json">JSON snapshot</a></div>
    </header>

    <iframe src="control.html" title="Live server controls" style="width:100%;height:1720px;border:0;border-radius:18px;margin-bottom:24px"></iframe>
    <p class="muted">Character statistics below are a page-load snapshot. Refresh this page to update them.</p>
    <?php if ($errors !== []): ?>
        <section class="full errors" style="margin-bottom: 16px">
            <h2>Database connection warnings</h2>
            <div class="muted"><?= htmlspecialchars(implode(' · ', $errors), ENT_QUOTES) ?></div>
        </section>
    <?php endif; ?>

    <div class="grid">
        <?php foreach ($cards as $card): ?>
            <div class="card">
                <div class="label"><?= htmlspecialchars($card['label'], ENT_QUOTES) ?></div>
                <div class="value"><?= htmlspecialchars((string) $card['value'], ENT_QUOTES) ?></div>
                <div class="muted"><?= htmlspecialchars((string) $card['hint'], ENT_QUOTES) ?></div>
            </div>
        <?php endforeach; ?>

        <section class="half">
            <h2>Server information</h2>
            <dl>
                <?php foreach ($serverInfo as $label => $value): ?>
                    <dt><?= htmlspecialchars($label, ENT_QUOTES) ?></dt>
                    <dd><?= htmlspecialchars((string) $value, ENT_QUOTES) ?></dd>
                <?php endforeach; ?>
            </dl>
        </section>

        <section class="half">
            <h2>Module status</h2>
            <dl>
                <?php foreach ($moduleInfo as $label => $value): ?>
                    <dt><?= htmlspecialchars($label, ENT_QUOTES) ?></dt>
                    <dd><?= htmlspecialchars((string) $value, ENT_QUOTES) ?></dd>
                <?php endforeach; ?>
            </dl>
        </section>

        <section class="half">
            <h2>Faction population</h2>
            <?php $maxFaction = max(1, max($factionCounts)); ?>
            <?php foreach ($factionCounts as $label => $count): ?>
                <p><strong><?= htmlspecialchars($label, ENT_QUOTES) ?></strong> <span class="muted"><?= $count ?> characters</span></p>
                <div class="bar"><span style="width: <?= (int) (($count / $maxFaction) * 100) ?>%"></span></div>
            <?php endforeach; ?>
        </section>

        <section class="half">
            <h2>Class breakdown</h2>
            <table>
                <thead><tr><th>Class</th><th>Total</th></tr></thead>
                <tbody>
                <?php foreach ($classBreakdown as $row): ?>
                    <tr><td><?= htmlspecialchars(class_name((int) $row['class']), ENT_QUOTES) ?></td><td><?= (int) $row['total'] ?></td></tr>
                <?php endforeach; ?>
                <?php if ($classBreakdown === []): ?><tr><td colspan="2" class="muted">No character rows yet.</td></tr><?php endif; ?>
                </tbody>
            </table>
        </section>

        <section class="wide">
            <h2>Characters snapshot</h2>
            <table>
                <thead><tr><th>Name</th><th>Level</th><th>Class</th><th>Faction</th><th>Online</th><th>Played</th></tr></thead>
                <tbody>
                <?php foreach ($recentCharacters as $row): ?>
                    <tr>
                        <td><?= htmlspecialchars((string) $row['name'], ENT_QUOTES) ?></td>
                        <td><?= (int) $row['level'] ?></td>
                        <td><?= htmlspecialchars(class_name((int) $row['class']), ENT_QUOTES) ?></td>
                        <td><?= htmlspecialchars(race_faction((int) $row['race']), ENT_QUOTES) ?></td>
                        <td class="<?= ((int) $row['online']) === 1 ? 'status-on' : 'status-off' ?>"><?= ((int) $row['online']) === 1 ? 'Yes' : 'No' ?></td>
                        <td><?= duration_text((int) $row['totaltime']) ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if ($recentCharacters === []): ?><tr><td colspan="6" class="muted">No characters yet.</td></tr><?php endif; ?>
                </tbody>
            </table>
        </section>

        <section class="card" style="grid-column: span 4">
            <h2>Seeded friend accounts</h2>
            <table>
                <thead><tr><th>User</th><th>Online</th></tr></thead>
                <tbody>
                <?php foreach ($initialUsers as $row): ?>
                    <tr>
                        <td><?= htmlspecialchars((string) $row['username'], ENT_QUOTES) ?></td>
                        <td class="<?= ((int) $row['online']) === 1 ? 'status-on' : 'status-off' ?>"><?= ((int) $row['online']) === 1 ? 'Yes' : 'No' ?></td>
                    </tr>
                <?php endforeach; ?>
                <?php if ($initialUsers === []): ?><tr><td colspan="2" class="muted">Seed service has not run yet.</td></tr><?php endif; ?>
                </tbody>
            </table>
        </section>
    </div>
</main>
</body>
</html>
