package mx.sigic.gs.wpsdownload.excel;

import org.geoserver.wps.download.DownloadServiceEncoder;
import org.geotools.api.data.simple.SimpleFeatureCollection;
import org.geotools.api.feature.simple.SimpleFeatureType;
import org.geotools.api.feature.simple.SimpleFeature;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.io.WKTWriter;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.OutputStream;
import java.util.Map;
import java.util.Set;

import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.ss.usermodel.*;

@Component
public class XlsDownloadServiceEncoder implements DownloadServiceEncoder {

    public static final String MIME_XLS = "application/vnd.ms-excel";

    @Override
    public Set<String> getOutputMimeTypes() { return Set.of(MIME_XLS); }

    @Override
    public void encode(SimpleFeatureCollection features,
                       OutputStream out,
                       Map<String, Object> encoderParams,
                       org.opengis.util.ProgressListener listener) throws IOException {

        try (HSSFWorkbook wb = new HSSFWorkbook()) { // NO streaming en HSSF
            Sheet sheet = wb.createSheet("data");

            SimpleFeatureType schema = features.getSchema();
            int colCount = schema.getAttributeCount();

            // Header
            Row header = sheet.createRow(0);
            for (int c = 0; c < colCount; c++) {
                header.createCell(c).setCellValue(schema.getDescriptor(c).getLocalName());
            }

            // Estilos
            CreationHelper ch = wb.getCreationHelper();
            CellStyle dateStyle = wb.createCellStyle();
            dateStyle.setDataFormat(ch.createDataFormat().getFormat("yyyy-mm-dd hh:mm:ss"));

            WKTWriter wkt = new WKTWriter();
            int r = 1;

            try (var it = features.features()) {
                while (it.hasNext()) {
                    SimpleFeature f = it.next();
                    Row row = sheet.createRow(r++);
                    for (int c = 0; c < colCount; c++) {
                        Object v = f.getAttribute(c);
                        Cell cell = row.createCell(c);
                        if (v == null) {
                            cell.setBlank();
                        } else if (v instanceof Geometry) {
                            cell.setCellValue(wkt.write((Geometry) v));
                        } else if (v instanceof Number) {
                            cell.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            cell.setCellValue((java.util.Date) v);
                            cell.setCellStyle(dateStyle);
                        } else {
                            cell.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }

            for (int c = 0; c < Math.min(colCount, 25); c++) sheet.autoSizeColumn(c);

            wb.write(out);
        }
    }
}
