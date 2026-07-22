<?php
/**
 * SweetCheat Mailer using Postfix sendmail
 */

function sendMail($to, $subject, $bodyHtml, $type = 'generic') {
    $pdo = getDB();
    $from = 'SweetCheat <noreply@sayfespace.online>';
    $headers = [
        'From: ' . $from,
        'Reply-To: ' . $from,
        'MIME-Version: 1.0',
        'Content-Type: text/html; charset=UTF-8',
        'X-Mailer: SweetCheat Mailer/1.0'
    ];

    $log = ['recipient' => $to, 'subject' => $subject, 'type' => $type];

    $success = mail($to, $subject, $bodyHtml, implode("\r\n", $headers));

    if (!$success) {
        $log['status'] = 'failed';
        $log['error'] = error_get_last()['message'] ?? 'mail() returned false';
    } else {
        $log['status'] = 'sent';
        $log['error'] = null;
    }

    try {
        $stmt = $pdo->prepare("INSERT INTO email_log (recipient, subject, type, status, error, created_at) VALUES (?, ?, ?, ?, ?, strftime('%s','now'))");
        $stmt->execute([$log['recipient'], $log['subject'], $log['type'], $log['status'], $log['error']]);
    } catch (Exception $e) {
        error_log("Email log failed: " . $e->getMessage());
    }

    return $success;
}

function getEmailTemplate($template, $vars) {
    $baseUrl = 'https://' . ($_SERVER['HTTP_HOST'] ?? 'sayfespace.online');
    $templates = [
        'verify' => function($v) use ($baseUrl) {
            $link = $baseUrl . '/sweetcheat/verify-email?token=' . urlencode($v['token']);
            return "
            <html><body style='font-family:Inter,Segoe UI,Arial,sans-serif; background:#050507; color:#f8fafc; padding:20px;'>
            <div style='max-width:480px; margin:0 auto; background:#0f1016; border:1px solid #232333; border-radius:14px; padding:32px;'>
                <h1 style='font-family:\"Rajdhani\",sans-serif; color:#00f0ff; margin-bottom:16px;'>SweetCheat E-Mail bestätigen</h1>
                <p style='color:#94a3b8; line-height:1.6;'>Danke für deine Registrierung! Klicke auf den Button, um deinen Account zu aktivieren.</p>
                <a href='{$link}' style='display:inline-block; background:#00f0ff; color:#050507; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700; margin:20px 0;'>E-Mail bestätigen</a>
                <p style='color:#94a3b8; font-size:13px;'>Falls der Button nicht funktioniert, kopiere diesen Link: {$link}</p>
            </div>
            </body></html>";
        },
        'reset' => function($v) use ($baseUrl) {
            $link = $baseUrl . '/sweetcheat/reset-password?token=' . urlencode($v['token']);
            return "
            <html><body style='font-family:Inter,Segoe UI,Arial,sans-serif; background:#050507; color:#f8fafc; padding:20px;'>
            <div style='max-width:480px; margin:0 auto; background:#0f1016; border:1px solid #232333; border-radius:14px; padding:32px;'>
                <h1 style='font-family:\"Rajdhani\",sans-serif; color:#00f0ff; margin-bottom:16px;'>Passwort zurücksetzen</h1>
                <p style='color:#94a3b8; line-height:1.6;'>Klicke auf den Button, um ein neues Passwort für deinen SweetCheat-Account zu setzen. Der Link ist 1 Stunde gültig.</p>
                <a href='{$link}' style='display:inline-block; background:#ff3864; color:#fff; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700; margin:20px 0;'>Neues Passwort setzen</a>
                <p style='color:#94a3b8; font-size:13px;'>Falls der Button nicht funktioniert: {$link}</p>
            </div>
            </body></html>";
        },
        'welcome' => function($v) use ($baseUrl) {
            return "
            <html><body style='font-family:Inter,Segoe UI,Arial,sans-serif; background:#050507; color:#f8fafc; padding:20px;'>
            <div style='max-width:480px; margin:0 auto; background:#0f1016; border:1px solid #232333; border-radius:14px; padding:32px;'>
                <h1 style='font-family:\"Rajdhani\",sans-serif; color:#00f0ff; margin-bottom:16px;'>Willkommen bei SweetCheat!</h1>
                <p style='color:#94a3b8; line-height:1.6;'>Dein Account ist jetzt aktiv. Lade die Windows-App herunter oder stöbere direkt in der Trainer-Datenbank.</p>
                <a href='{$baseUrl}/sweetcheat/setup' style='display:inline-block; background:#00f0ff; color:#050507; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700; margin:20px 0;'>App herunterladen</a>
                <a href='{$baseUrl}/sweetcheat/games' style='display:inline-block; background:#232333; color:#f8fafc; padding:14px 28px; border-radius:8px; text-decoration:none; font-weight:700; margin-left:10px;'>Spiele erkunden</a>
            </div>
            </body></html>";
        }
    ];

    if (!isset($templates[$template])) return '';
    return $templates[$template]($vars);
}
