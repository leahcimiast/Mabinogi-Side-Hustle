"""Player-facing summaries; detailed scanner messages stay in the local log."""
import re


def action_step(message, action):
    countdown=re.search(r'([123]) 秒後開始',message)
    if countdown:return f'{countdown[1]} 秒後開始，正在切回遊戲；F8 可暫停。'
    if action=='庫存盤點':
        if '頂端' in message:return '準備盤點公用保管箱。'
        if '結束' in message or '已由頂端掃描到底' in message:return '盤點結束，請查看庫存與缺額。'
        return '正在盤點公用保管箱，請勿操作遊戲。'
    if action=='素材領取':
        if '已領取' in message:return '素材已領取。'
        if '等待' in message:return '等待遊戲回應。'
        return '正在領取素材，請勿操作遊戲。'
    if action=='任務交付':
        if '完成' in message:return '正在確認任務完成。'
        if '跳過' in message or '略過' in message:return '略過未找到的任務，繼續下一項。'
        return '正在交付任務，請勿操作遊戲。'
    return '準備執行。'


def stop_message(message):
    if any(token in message for token in ('OCR','捲動影像','堆疊位置','跨距','540 px','邊界返回','格位')):
        return '無法完整辨識目前畫面；請確認遊戲頁面後重新開始。詳細原因請查看除錯紀錄。'
    return message
