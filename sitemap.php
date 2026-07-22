<?php
require_once __DIR__ . '/auth-lib.php';
$pdo = getDB();
header('Content-Type: application/xml');

echo '<?xml version="1.0" encoding="UTF-8"?>\n';
echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n      xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"\n      xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n';

$base = 'https://sayfespace.online/trainerhub';
$pages = [
    ['loc' => $base . '/', 'priority' => '1.0', 'changefreq' => 'daily'],
    ['loc' => $base . '/games', 'priority' => '0.9', 'changefreq' => 'daily'],
    ['loc' => $base . '/public-db', 'priority' => '0.9', 'changefreq' => 'daily'],
    ['loc' => $base . '/blog', 'priority' => '0.8', 'changefreq' => 'weekly'],
    ['loc' => $base . '/login', 'priority' => '0.5', 'changefreq' => 'monthly'],
    ['loc' => $base . '/register', 'priority' => '0.5', 'changefreq' => 'monthly'],
    ['loc' => $base . '/checkout', 'priority' => '0.7', 'changefreq' => 'weekly'],
];
foreach ($pages as $p) {
    echo "\t<url\u003e\n";
    echo "\t\t<loc>" . htmlspecialchars($p['loc']) . "</loc\u003e\n";
    echo "\t\t<priority>{$p['priority']}</priority\u003e\n";
    echo "\t\t<changefreq>{$p['changefreq']}</changefreq\u003e\n";
    echo "\t</url\u003e\n";
}

// Games detail pages
$stmt = $pdo->query("SELECT slug, updated_at FROM games WHERE is_active = 1");
while ($g = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $url = $base . '/game/' . urlencode($g['slug']);
    $lastmod = !empty($g['updated_at']) ? date('Y-m-d', $g['updated_at']) : date('Y-m-d');
    echo "\t<url\u003e\n";
    echo "\t\t<loc>" . htmlspecialchars($url) . "</loc\u003e\n";
    echo "\t\t<lastmod>{$lastmod}</lastmod\u003e\n";
    echo "\t\t<priority>0.8</priority\u003e\n";
    echo "\t\t<changefreq>weekly</changefreq\u003e\n";
    echo "\t</url\u003e\n";
}

// Blog posts
$stmt = $pdo->query("SELECT slug, updated_at FROM blog_posts WHERE published = 1");
while ($b = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $url = $base . '/blog/' . urlencode($b['slug']);
    $lastmod = !empty($b['updated_at']) ? date('Y-m-d', $b['updated_at']) : date('Y-m-d');
    echo "\t<url\u003e\n";
    echo "\t\t<loc>" . htmlspecialchars($url) . "</loc\u003e\n";
    echo "\t\t<lastmod>{$lastmod}</lastmod\u003e\n";
    echo "\t\t<priority>0.7</priority\u003e\n";
    echo "\t\t<changefreq>monthly</changefreq\u003e\n";
    echo "\t</url\u003e\n";
}

echo '</urlset>';
