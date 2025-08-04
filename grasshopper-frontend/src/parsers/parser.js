import exportFromJSON from "export-from-json";

export const excelParser = () => {
  function exportDataFromJSON(data, newFileName, fileExportType) {
    if (!data) return;
    try {
      const fileName = newFileName || "exported-data";
      const exportType = exportFromJSON.types[fileExportType || "xls"];
      exportFromJSON({ data, fileName, exportType });
    } catch (e) {
      console.log(e);
    }
  }

  return {
    exportDataFromJSON,
  };
};