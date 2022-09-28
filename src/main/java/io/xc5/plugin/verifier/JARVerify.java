package io.xc5.plugin.verifier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.stream.Collectors;

public class JARVerify {


  private static final String PROPERTIES_FILE_SUFFIX = ".lib.output.list";
  public static final String LIST_FILE_SUFFIX = ".lib.list";
  private static Logger logger = LoggerFactory.getLogger(JARVerify.class);
  private static List<String> passingModule = new ArrayList<>();
  private static List<String> failingModule = new ArrayList<>();

  // Read the Jars from the list,
  // Check if the accordiing .o file is properly generated.
  public static void main(String[] args) {
    List<File> workdirs = new LinkedList<>();
    if (args.length >= 1) {
      for (String f: args) {
        if (f.equals("-v")) {
          Utils.initLoggers(true, -1);
        } else if (f.startsWith("-logLevel=")) {
          Utils.initLoggers(false, Integer.parseInt(f.substring("-logLevel=".length()), 10));
        } else if (new File(f).exists()) {
          workdirs.add(new File(f));
        }
      }
    }

    for (File f: workdirs) {
      logger.info("Walking in {}", f.getAbsolutePath());
      readAllJarsAndObjects(f.getAbsolutePath());
    }

    logger.info("-------------------------");
    logger.info(" Jar-WHIRL Level Verify  ");
    logger.info("-------------------------");
    logger.info("Overall passing rate: {}", ((double) B2WVerify.passingJar.size()) / (B2WVerify.failingJar.size() + B2WVerify.passingJar.size()));
    logger.info("Overall passing count : {}", B2WVerify.passingJar.size());
    logger.info("Overall failing count : {}", B2WVerify.failingJar.size());

    logger.info("-----------------------------------");
    logger.info(" Target(Module) Level Verify       ");
    logger.info("-----------------------------------");
    logger.info("Overall passing rate: {}", ((double) passingModule.size()) / (failingModule.size() + passingModule.size()));
    logger.info("Overall passing count : {}", passingModule.size());
    logger.info("Overall failing count : {}", failingModule.size());

    double b2wPassRate = ((double) B2WVerify.passingJar.size()) / (B2WVerify.failingJar.size() + B2WVerify.passingJar.size());
    double jarPassRate = ((double) passingModule.size()) / (failingModule.size() + passingModule.size());
    // NaN here indicates 0 in pass and fail, thus in general it is passing.
    if (!Double.isNaN(b2wPassRate) && !(b2wPassRate == 1.0)) {
      System.exit(1);
    } else if (!Double.isNaN(jarPassRate) && !(jarPassRate == 1.0)) {
      System.exit(2);
    }
  }

  private static void readAllJarsAndObjects(String folderName) {
    logger.info("Start processing ...");
    // for each .o.properties file, open its .list file and .properties file, see if this works.
    List<File> lst = listFilesForFolder(new File(folderName));
    List<String> candidates = new ArrayList<>();
    Map<String, List<String>> objectList = new HashMap<>();
    Map<String, List<String>> jarList = new HashMap<>();
    for (File oneFile: lst) {
      if (oneFile.getName().endsWith(".o")) {
        // mark possible candidate
        candidates.add(oneFile.getName().substring(0, oneFile.getName().length() - 1));
      } else if (oneFile.getName().endsWith(PROPERTIES_FILE_SUFFIX)) {
        // read o files
        objectList.put(oneFile.getName().replaceAll(PROPERTIES_FILE_SUFFIX, ""),
                Utils.readListFromFile(oneFile.getAbsolutePath()));
      } else if (oneFile.getName().endsWith(LIST_FILE_SUFFIX)) {
        // read jar list
        jarList.put(oneFile.getName().replaceAll(LIST_FILE_SUFFIX, ""),
                Utils.readListFromFile(oneFile.getAbsolutePath()));
      }
    }

    HashSet<String> allJars = new HashSet<>();
    long totalSize = allJars.stream().mapToLong(x-> new File(x).length()).sum();
    logger.info(" Got jars list count: {}",  jarList.size());
    logger.info(" Total size of all related Jars : {} Bytes, or {} MB", totalSize, (double) totalSize / 1024.0 / 1024.0);
    logger.info(" Got objects list count: {} ", objectList.size());

    logger.info(" Removing folders in jar/object lists ...");
    jarList.forEach((key, value) -> {
      value.removeAll(value.stream()
              .filter(fileOrFolder -> new File(fileOrFolder).isDirectory())
              .collect(Collectors.toList()));
    });

    objectList.forEach((key, value) -> {
      value.removeAll(value.stream()
              .filter(fileOrFolder -> new File(fileOrFolder).isDirectory())
              .collect(Collectors.toList()));
    });

    jarList.forEach((key, value) -> allJars.addAll(value));

    jarList.forEach((jarFileName, jarFilesList) -> {
      logger.info(" - Jar file - : {}", jarFileName);
    });

    objectList.forEach((objectFileName, libraryObjectList) -> {
      boolean failed = false;
      logger.info(" - Object file - : {}", objectFileName);
      if (!jarList.containsKey(objectFileName)) {
        logger.info("Missing JAR info for object : {} ", objectFileName);
        failingModule.add(objectFileName);
        return;
      }

      if (jarList.get(objectFileName).size() != libraryObjectList.size()) {
        logger.info("Suspicious outcome : {}", objectFileName);
        logger.info("Jar size : {}", jarList.get(objectFileName).size());
        logger.info("Object size : {}",  libraryObjectList.size());
        failed = true;
      }

      List<String> libraryNames = libraryObjectList.stream().map(x -> new File(x).getName()).collect(Collectors.toList());
      List<String> jarNames = jarList.get(objectFileName).stream()
              .map(x -> new File(x).getName().replaceAll("\\.", "-") + ".o")
                                   .collect(Collectors.toList());
      for (String x : libraryNames) {
        logger.info("one library with .o output: {}", x);
      }
      for (String x : jarNames) {
        logger.info("one library with .jar file: {}", x);
      }

      libraryNames.removeAll(jarNames);
      if (libraryNames.size() != 0) {
        for (String oneObject : libraryNames) {
          logger.info("Outstandinig object lacking jar counterpart : \"{}\", len={}", oneObject, oneObject.length());
          failingModule.add(objectFileName);
          return;
        }
      }

      if (failed) {
        failingModule.add(objectFileName);
        return;
      }

      logger.info("Passing Jar-Level Check: {}",  objectFileName);
      passingModule.add(objectFileName);

      // Second Stage, verify the content of a Jar and an object.
      Map<String, String> jarNameToFileMap = jarList.get(objectFileName)
              .stream()
              .collect(Collectors.toMap(x->new File(x).getName().replaceAll("\\.", "-") + ".o", x->x));
      Map<String, String> libraryNameToFileMap = libraryObjectList
              .stream()
              .collect(Collectors.toMap(x-> new File(x).getName(), x->x));
      Map<String, String> jarToLibraryFileMap = jarNameToFileMap
              .entrySet()
              .stream()
              .collect(Collectors.toMap((x) -> x.getValue(), (x) -> libraryNameToFileMap.get(x.getKey())));
      B2WVerify.performVerify(jarToLibraryFileMap);
    });
  }

  public static List<File> listFilesForFolder(final File folder) {
    List<File> lst = new ArrayList<>();
    for (final File fileEntry : Objects.requireNonNull(folder.listFiles())) {
      if (fileEntry.isDirectory()) {
        logger.info("Not entering the directory : " + fileEntry.getName());
        // listFilesForFolder(fileEntry);
      } else {
        lst.add(fileEntry);
      }
    }
    return lst;
  }

  public static void readJarContent() {
    JarFile jarFile = null;
    try {
      jarFile = new JarFile("yourJarFileName.jar");
    } catch (IOException e) {
      e.printStackTrace();
      return;
    }
    Enumeration enums = jarFile.entries();
    while (enums.hasMoreElements()) {
      process(enums.nextElement());
    }
  }

  private static void process(Object obj) {
    JarEntry entry = (JarEntry)obj;
    String name = entry.getName();
    long size = entry.getSize();
    long compressedSize = entry.getCompressedSize();
    System.out.println(
            name + "\t" + size + "\t" + compressedSize);
  }

}
