package mx.sigic.wps.excel;

import java.io.OutputStream;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;  // XLS
import org.apache.poi.ss.usermodel.*;
import org.geoserver.wps.ppio.ComplexPPIO;
import org.geotools.api.data.simple.SimpleFeatureCollection;
import org.geotools.api.data.simple.SimpleFeatureIterator;
import org.geotools.api.feature.simple.SimpleFeature;
import org.geotools.api.feature.simple.SimpleFeatureType;
import org.geotools.api.feature.type.AttributeDescriptor;
import org.locationtech.jts.geom.Geometry;

public class XlsPPIO extends ComplexPPIO {

    public XlsPPIO() {
        super(OutputStream.class, SimpleFeatureCollection.class,
              "application/vnd.ms-excel");
    }

    @Override
    public void encode(Object value, OutputStream os) throws Exception {
        SimpleFeatureCollection fc = (SimpleFeatureCollection) value;
        try (Workbook wb = new HSSFWorkbook()) {
            Sheet sh = wb.createSheet("data");
            SimpleFeatureType ft = fc.getSchema();

            Row header = sh.createRow(0);
            for (int i = 0; i < ft.getAttributeCount(); i++) {
                AttributeDescriptor ad = ft.getDescriptor(i);
                header.createCell(i).setCellValue(ad.getLocalName());
            }

            int r = 1;
            try (SimpleFeatureIterator it = fc.features()) {
                while (it.hasNext()) {
                    SimpleFeature f = it.next();
                    Row row = sh.createRow(r++);
                    for (int i = 0; i < ft.getAttributeCount(); i++) {
                        Object v = f.getAttribute(i);
                        Cell c = row.createCell(i);
                        if (v == null) { c.setBlank(); continue; }
                        if (v instanceof Number) {
                            c.setCellValue(((Number) v).doubleValue());
                        } else if (v instanceof java.util.Date) {
                            c.setCellValue((java.util.Date) v);
                        } else if (v instanceof Geometry) {
                            c.setCellValue(((Geometry) v).toText());
                        } else {
                            c.setCellValue(String.valueOf(v));
                        }
                    }
                }
            }
            wb.write(os);
        }
    }

    @Override
    public String getFileExtension() { return "xls"; }

    @Override
    public PPIODirection getDirection() { return PPIODirection.ENCODING; }
}
