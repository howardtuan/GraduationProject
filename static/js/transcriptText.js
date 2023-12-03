var transcriptText='';
function showTranscript() {
    $('#transcript-content').text(transcript_download);
}
function downloadTranscript() {
    transcriptText = transcript_download;  // 這裡的 `transcript` 是逐字稿的文字內容
    

    // 建立 Blob 物件
    var blob = new Blob([transcriptText], { type: 'text/plain' });

    // 建立下載連結
    var downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(blob);
    downloadLink.download = 'transcript.txt';

    // 觸發點擊事件下載檔案
    downloadLink.click();
}