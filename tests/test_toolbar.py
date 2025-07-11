import pytest
from nebulastudio.application import NebulaStudioApplication
from PyQt6.QtCore import Qt


@pytest.fixture
def app():
    return NebulaStudioApplication([])


@pytest.fixture
def window(app):
    return app.new_window()


def test_window_flags(window):
    flags = window.image_prop_toolbar.windowFlags()
    type = flags & Qt.WindowType.WindowType_Mask

    if type == Qt.WindowType.Window:
        text = "Qt::Window"
    elif type == Qt.WindowType.Dialog:
        text = "Qt::Dialog"
    elif type == Qt.WindowType.Drawer:
        text = "Qt::Drawer"
    elif type == Qt.WindowType.Popup:
        text = "Qt::Popup"
    elif type == Qt.WindowType.Tool:
        text = "Qt::Tool"
    elif type == Qt.WindowType.ToolTip:
        text = "Qt::ToolTip"
    elif type == Qt.WindowType.SplashScreen:
        text = "Qt::SplashScreen"
    else:
        text = ""

    if flags & Qt.WindowType.MSWindowsFixedSizeDialogHint:
        text += "\n| Qt::MSWindowsFixedSizeDialogHint"
    if flags & Qt.WindowType.X11BypassWindowManagerHint:
        text += "\n| Qt::X11BypassWindowManagerHint"
    if flags & Qt.WindowType.FramelessWindowHint:
        text += "\n| Qt::FramelessWindowHint"
    if flags & Qt.WindowType.NoDropShadowWindowHint:
        text += "\n| Qt::NoDropShadowWindowHint"
    if flags & Qt.WindowType.WindowTitleHint:
        text += "\n| Qt::WindowTitleHint"
    if flags & Qt.WindowType.WindowSystemMenuHint:
        text += "\n| Qt::WindowSystemMenuHint"
    if flags & Qt.WindowType.WindowMinimizeButtonHint:
        text += "\n| Qt::WindowMinimizeButtonHint"
    if flags & Qt.WindowType.WindowMaximizeButtonHint:
        text += "\n| Qt::WindowMaximizeButtonHint"
    if flags & Qt.WindowType.WindowCloseButtonHint:
        text += "\n| Qt::WindowCloseButtonHint"
    if flags & Qt.WindowType.WindowContextHelpButtonHint:
        text += "\n| Qt::WindowContextHelpButtonHint"
    if flags & Qt.WindowType.WindowShadeButtonHint:
        text += "\n| Qt::WindowShadeButtonHint"
    if flags & Qt.WindowType.WindowStaysOnTopHint:
        text += "\n| Qt::WindowStaysOnTopHint"
    if flags & Qt.WindowType.WindowStaysOnBottomHint:
        text += "\n| Qt::WindowStaysOnBottomHint"
    if flags & Qt.WindowType.CustomizeWindowHint:
        text += "\n| Qt::CustomizeWindowHint"

    print(text)
