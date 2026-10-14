#include <QApplication>
#include <QClipboard>
#include <QCloseEvent>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFormLayout>
#include <QHostAddress>
#include <QLabel>
#include <QLineEdit>
#include <QMenu>
#include <QNetworkInterface>
#include <QProcess>
#include <QProcessEnvironment>
#include <QPushButton>
#include <QRandomGenerator>
#include <QStandardPaths>
#include <QStyle>
#include <QSystemTrayIcon>
#include <QTcpSocket>
#include <QTimer>
#include <QUrl>
#include <QVBoxLayout>

static bool privateAddress(const QString &text) {
    QHostAddress address(text);
    if (address.protocol() != QAbstractSocket::IPv4Protocol) return false;
    const auto ip = address.toIPv4Address();
    return (ip >> 24) == 10 || (ip >> 20) == 0xac1 || (ip >> 16) == 0xc0a8;
}

class Window final : public QWidget {
    QProcess engine;
    QTimer timer;
    QTcpSocket probe;
    QSystemTrayIcon tray;
    QMenu menu;
    QLineEdit *host, *device, *endpoint;
    QLabel *status;
    QPushButton *startButton, *stopButton;
    QString token, activeHost;
    bool quitting = false;
    QString logPath;

    void setRunning(bool running) {
        host->setEnabled(!running);
        device->setEnabled(!running);
        startButton->setEnabled(!running);
        stopButton->setEnabled(running);
    }
    void stop() {
        if (engine.state() == QProcess::NotRunning) return;
        status->setText(QStringLiteral("正在停止访问…"));
        stopButton->setEnabled(false);
        timer.stop();
        probe.abort();
        engine.terminate();
        QTimer::singleShot(2000, this, [this] {
            if (engine.state() != QProcess::NotRunning) engine.kill();
        });
    }
    void quit() {
        quitting = true;
        if (engine.state() == QProcess::NotRunning) QApplication::quit();
        else stop();
    }
    void start() {
        if (!privateAddress(host->text()) || !privateAddress(device->text())) {
            status->setText(QStringLiteral("请填写电脑和设备的有效局域网 IPv4 地址"));
            return;
        }
        const QString program = QCoreApplication::applicationDirPath() + "/engine/QZdeskMcpEngine.exe";
        if (!QFile::exists(program)) {
            status->setText(QStringLiteral("缺少 MCP 引擎，请使用包含 engine 目录的完整发行包"));
            return;
        }
        activeHost = host->text();
        engine.setProgram(program);
        engine.setArguments({"serve", "--transport", "streamable-http", "--host", activeHost,
            "--port", "8000", "--auth-key", token, "--ip-allowlist", device->text(), "--tools", "Snapshot"});
        auto environment = QProcessEnvironment::systemEnvironment();
        environment.insert("ANONYMIZED_TELEMETRY", "false");
        engine.setProcessEnvironment(environment);
        engine.setStandardOutputFile(logPath, QIODevice::Append);
        engine.setStandardErrorFile(logPath, QIODevice::Append);
        endpoint->setText("http://" + activeHost + ":8000/mcp");
        setRunning(true);
        status->setText(QStringLiteral("正在启动电脑服务…"));
        engine.start();
    }
protected:
    void closeEvent(QCloseEvent *event) override {
        if (!quitting && tray.isVisible()) {
            hide();
            event->ignore();
        } else if (engine.state() != QProcess::NotRunning) {
            event->ignore();
            quit();
        } else event->accept();
    }
public:
    Window() {
        setWindowTitle(QStringLiteral("QZdesk · 电脑连接器"));
        resize(720, 620);
        setMinimumSize(540, 580);
        auto icon = style()->standardIcon(QStyle::SP_ComputerIcon);
        setWindowIcon(icon);
        for (int i = 0; i < 8; ++i) token += QString::number(QRandomGenerator::system()->generate(), 16).rightJustified(8, '0');
        const auto directory = QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation);
        QDir().mkpath(directory);
        logPath = directory + "/server.log";
        auto layout = new QVBoxLayout(this);
        layout->setContentsMargins(28, 28, 28, 28);
        layout->setSpacing(16);
        auto brand = new QLabel("QZdesk / COMPUTER LINK");
        brand->setObjectName("brand");
        layout->addWidget(brand);
        auto title = new QLabel(QStringLiteral("连接你的工作现场"));
        title->setObjectName("title");
        layout->addWidget(title);
        auto caption = new QLabel(QStringLiteral("按需读取窗口和网页，让语音助手理解你正在做的事。"));
        caption->setWordWrap(true);
        layout->addWidget(caption);
        status = new QLabel(QStringLiteral("尚未启动 · 只读模式"));
        status->setObjectName("status");
        status->setWordWrap(true);
        layout->addWidget(status);
        auto card = new QWidget;
        card->setObjectName("card");
        auto form = new QFormLayout(card);
        form->setContentsMargins(20, 20, 20, 20);
        form->setSpacing(14);
        form->setRowWrapPolicy(QFormLayout::WrapLongRows);
        host = new QLineEdit;
        for (const auto &address : QNetworkInterface::allAddresses()) {
            if (privateAddress(address.toString())) { host->setText(address.toString()); break; }
        }
        device = new QLineEdit;
        device->setPlaceholderText("192.168.1.50");
        endpoint = new QLineEdit;
        endpoint->setReadOnly(true);
        form->addRow(QStringLiteral("电脑 IPv4"), host);
        form->addRow(QStringLiteral("允许的设备 IPv4"), device);
        form->addRow(QStringLiteral("连接地址"), endpoint);
        layout->addWidget(card);
        auto buttons = new QHBoxLayout;
        startButton = new QPushButton(QStringLiteral("启动连接"));
        startButton->setObjectName("primary");
        stopButton = new QPushButton(QStringLiteral("停止访问"));
        stopButton->setEnabled(false);
        auto copy = new QPushButton(QStringLiteral("复制密钥"));
        buttons->addWidget(startButton);
        buttons->addWidget(stopButton);
        buttons->addWidget(copy);
        layout->addLayout(buttons);
        auto note = new QLabel(QStringLiteral("仅允许指定设备访问，不点击、不输入、不修改文件。\n首次连接仍需填写地址与密钥；密钥在退出后重新生成。仅限可信局域网。\n关闭窗口后驻留托盘；退出会停止服务。"));
        note->setWordWrap(true);
        layout->addWidget(note);
        auto logs = new QPushButton(QStringLiteral("打开日志目录"));
        layout->addWidget(logs, 0, Qt::AlignLeft);
        layout->addStretch();
        connect(logs, &QPushButton::clicked, this, [directory] { QDesktopServices::openUrl(QUrl::fromLocalFile(directory)); });
        connect(startButton, &QPushButton::clicked, this, [this] { start(); });
        connect(stopButton, &QPushButton::clicked, this, [this] { stop(); });
        connect(copy, &QPushButton::clicked, this, [this] {
            QApplication::clipboard()->setText(token);
            status->setText(QStringLiteral("密钥已复制，请仅粘贴到你的设备，完成后清除剪贴板"));
        });
        connect(&engine, &QProcess::started, this, [this] { timer.start(3000); });
        connect(&engine, &QProcess::errorOccurred, this, [this](QProcess::ProcessError error) {
            if (error == QProcess::FailedToStart) {
                setRunning(false);
                status->setText(QStringLiteral("引擎无法启动，请检查完整发行包和日志"));
                if (quitting) QApplication::quit();
            }
        });
        connect(&engine, qOverload<int, QProcess::ExitStatus>(&QProcess::finished), this,
            [this](int code, QProcess::ExitStatus) {
                timer.stop(); probe.abort(); setRunning(false);
                status->setText(QStringLiteral("服务已停止（退出码 %1）").arg(code));
                if (quitting) QApplication::quit();
            });
        connect(&timer, &QTimer::timeout, this, [this] {
            if (probe.state() == QAbstractSocket::UnconnectedState) probe.connectToHost(activeHost, 8000);
        });
        connect(&probe, &QTcpSocket::connected, this, [this] {
            status->setText(QStringLiteral("服务端口已监听 · 尚未确认设备连接"));
            probe.abort();
        });
        connect(&probe, &QTcpSocket::errorOccurred, this, [this](QAbstractSocket::SocketError) {
            status->setText(QStringLiteral("等待服务监听 · 长时间无响应请查看日志"));
        });
        menu.addAction(QStringLiteral("打开连接器"), this, [this] { showNormal(); raise(); activateWindow(); });
        menu.addAction(QStringLiteral("停止访问"), this, [this] { stop(); });
        menu.addSeparator();
        menu.addAction(QStringLiteral("退出"), this, [this] { quit(); });
        tray.setIcon(icon);
        tray.setToolTip("QZdesk 电脑连接器");
        tray.setContextMenu(&menu);
        connect(&tray, &QSystemTrayIcon::activated, this, [this](QSystemTrayIcon::ActivationReason reason) {
            if (reason == QSystemTrayIcon::DoubleClick) { showNormal(); raise(); }
        });
        if (QSystemTrayIcon::isSystemTrayAvailable()) tray.show();
    }
};

int main(int argc, char **argv) {
    QApplication app(argc, argv);
    app.setApplicationName("QZdeskConnector");
    app.setOrganizationName("QZdesk");
    app.setFont(QFont("Microsoft YaHei UI", 10));
    app.setStyleSheet("QWidget{background:#eef2f7;color:#172033;} QLabel#brand{color:#2563eb;font-weight:600;} QLabel#title{font-size:28px;font-weight:700;} QLabel#status{background:#dbeafe;color:#1e40af;padding:16px;border-radius:10px;} QWidget#card{background:white;border-radius:12px;} QLineEdit{background:white;border:1px solid #cbd5e1;border-radius:6px;padding:10px;selection-background-color:#2563eb;} QLineEdit:focus{border:1px solid #2563eb;} QPushButton{background:#e2e8f0;border:0;border-radius:7px;padding:12px;} QPushButton:hover{background:#cbd5e1;} QPushButton#primary{background:#2563eb;color:white;} QPushButton#primary:hover{background:#1d4ed8;} QPushButton:disabled{background:#e2e8f0;color:#64748b;}");
    Window window;
    window.show();
    return app.exec();
}
