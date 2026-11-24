const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5000";

const getBaseFileName = (fileName = "") => {
  const dotIndex = fileName.lastIndexOf(".");
  return dotIndex > 0 ? fileName.slice(0, dotIndex) : fileName;
};

export const handleUpload = async (
  file,
  language_input,
  setLoading,
  Set_Show_Language_Transcription_Button,
  Set_Show_Language_Summary_Button
) => {
  if (!file) {
    alert("Please select a file first.");
    return;
  }

  setLoading(true);
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language_input);

  try {
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    alert(data.message);
    Set_Show_Language_Transcription_Button(true);
    Set_Show_Language_Summary_Button(true);
  } catch (error) {
    alert("Error uploading file: " + error);
  } finally {
    setLoading(false);
  }
};

export const transcribe = async (
  file,
  language_transcription,
  setLoadingTranscription,
  Set_Show_Download_Transcription_Buttons
) => {
  setLoadingTranscription(true);
  const baseFileName = getBaseFileName(file?.name);

  console.log("API transcribe called with:", {
    baseFileName,
    language_transcription,
  });

  try {
    const url = `${API_BASE_URL}/transcribe?video_name=${encodeURIComponent(baseFileName)}&language=${encodeURIComponent(language_transcription)}`;
    console.log("Transcribe URL:", url);

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    Set_Show_Download_Transcription_Buttons(true);
    return data.result || "";
  } catch (error) {
    alert("Error during transcription: " + error);
    return "";
  } finally {
    setLoadingTranscription(false);
  }
};

export const summarize = async (
  file,
  language_summary,
  setLoadingSummary,
  Set_Show_Download_Summary_Buttons
) => {
  setLoadingSummary(true);
  const baseFileName = getBaseFileName(file?.name);

  try {
    const url = `${API_BASE_URL}/summarize?video_name=${encodeURIComponent(baseFileName)}&language=${encodeURIComponent(language_summary)}`;
    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    Set_Show_Download_Summary_Buttons(true);
    return data.result || "";
  } catch (error) {
    alert("Error during summary: " + error);
    return "";
  } finally {
    setLoadingSummary(false);
  }
};

export const handleSearch = async (keywords) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/search?keywords=${encodeURIComponent(keywords)}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.results || [];
  } catch (err) {
    console.error(err);
    alert("Error fetching search results: " + err);
    return [];
  }
};

export const getAllVideos = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/videos`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.videos || [];
  } catch (err) {
    console.error(err);
    alert("Error fetching all videos: " + err);
    return [];
  }
};

export const SummarizeForSearch = async (videoName, language = "en") => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/summarize?video_name=${encodeURIComponent(videoName)}&language=${encodeURIComponent(language)}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.result || "";
  } catch (error) {
    console.error("Error fetching summary:", error);
    return "";
  }
};

export const TranscribeForSearch = async (videoName, language = "en") => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/transcribe?video_name=${encodeURIComponent(videoName)}&language=${encodeURIComponent(language)}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return data.result || "";
  } catch (error) {
    console.error("Error fetching transcription:", error);
    return "";
  }
};