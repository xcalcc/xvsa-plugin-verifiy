package io.xc5.plugin.verifier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

public class B2WVerify {
  public static final String WHIRL_LIST_SUFFIX = ".W.list";
  public static final String JAR_VTABLES_SUFFIX = ".vtable";
  // This logger is by-default ou tput to file, not to console.
  private static Logger logger = LoggerFactory.getLogger(B2WVerify.class);

  public static List<String> passingJar = new ArrayList<>();
  public static List<String> failingJar = new ArrayList<>();

  private static String jarListFile = "";

  // Read the JAR list,
  // Find all classes in JARs
  // Get all WHIRL class symbol names for that JAR, (.o file)
  // Check if they are all matching.
  public static void main(String[] args) {
    if (args.length >= 1) {
      jarListFile = args[0];
    }
    performVerify(new HashMap<>());
  }

  static void performVerify(Map<String, String> allJarsAndObjectFiles) {
    allJarsAndObjectFiles.forEach(B2WVerify::verifyJarWithObject);
  }

  private static List<String> readJarList() {
    return Utils.readListFromFile(jarListFile);
  }

  /***
   * Verify one jar and one object(WHIRL) file
   * 1. Verify classes are present, class symbols are present
   * 2. Verify all functions in V-Tables are correct.
   * @param jarPath
   * @param whirlPath
   */
  public static void verifyJarWithObject(String jarPath, String whirlPath) {
    if (passingJar.contains(jarPath) || failingJar.contains(jarPath)){
      return;
    }
    boolean failed = false;
    logger.info("Verifying {} and {}", jarPath, whirlPath);

    // Get all class from Jar
    List<String> allJarClasses = new ArrayList<>();
    getAllJarContents(jarPath, allJarClasses);

    // Get all class symbols from object file.
    Map<String, List<String>> vtableObject = new HashMap<>();
    List<String> allObjectClasses = new ArrayList<>();
    getClassSymbolNamesFromList(whirlPath + WHIRL_LIST_SUFFIX, vtableObject, allObjectClasses);

    // Diff the two lists
    Set<String> allJarClassSet = new HashSet<>(allJarClasses);
    Set<String> allObjectClassSet = new HashSet<>(allObjectClasses);

    // Match the two lists
    if (allJarClassSet.size() != allObjectClassSet.size()) {
      logger.info("Jar and WHIRL classes count mismatch for {} and {}",  jarPath, whirlPath);
      logger.info("Jar reported: {} classes", allJarClassSet.size());
      logger.info("Whirl reported: {} classes", allObjectClassSet.size());
      failed = true;
    }
    Set<String> missingClass = new HashSet<>();
    allJarClassSet.forEach(x -> {
      if (!allObjectClassSet.contains(x)) {
        missingClass.add(x);
        logger.debug("Found missing class: {}",  x);
      } else {
        allObjectClassSet.remove(x);
      }
    });
    if (allObjectClassSet.size() > 0) {
      allObjectClassSet.forEach(x -> {
        logger.debug("Found redundant class: {}", x);
        missingClass.add(x);
      });
    }
    // V-Table check...
    Map<String, List<String>> vtablesJar = readVtableListFromJar(whirlPath);
    if (vtablesJar.size() != vtableObject.size()) {
      logger.info("Found difference in V-Table from jar and WHIRL counts: {} vs {}",
                  vtablesJar.size(), vtableObject.size());
      failed = true;
    }
    vtablesJar.forEach((ztvName, jarEntry) -> {
	    logger.debug("vtable-jar: [{}], jarEntry", ztvName);
    });
    vtableObject.forEach((ztvName, jarEntry) -> {
	    logger.debug("vtable-object: [{}], objectEntry: [{}]", ztvName, jarEntry.size());
    });
    vtablesJar.forEach((ztvName, jarEntry) -> {
      if (!vtableObject.containsKey(ztvName)) {
        logger.debug("Cannot find vTable entry {} in object.", ztvName);
        missingClass.add(ztvName);
        return;
      }
      List<String> objectEntry = vtableObject.get(ztvName);
      if (objectEntry.size() != jarEntry.size()) {
        logger.debug("A vTable entry {} has different size", ztvName);
        missingClass.add(ztvName);
        return;
      }
      objectEntry.removeAll(jarEntry);
      if (objectEntry.size() > 0) {
        logger.debug("A vTable entry {} has different content", ztvName);
        missingClass.add(ztvName);
      }
    });
    // diff.
    if (missingClass.size() != 0 || failed) {
      logger.error("B2W Verify over jar: {} has failed", jarPath);
      logger.error("missingClass : {}, {}", missingClass.size(), failed);
      failingJar.add(jarPath);
    } else {
      passingJar.add(jarPath);
    }
  }

  private static Map<String, List<String>> readVtableListFromJar(String whirlPath) {
    Map<String, List<String>> vtablesJar = new HashMap<>();
    getClassSymbolNamesFromList(whirlPath + JAR_VTABLES_SUFFIX, vtablesJar, new ArrayList<>());
    return vtablesJar;
  }

  /***
   * Use JarFile to extract class names in Jar.
   * @param jarPath
   * @param allJarClasses
   */
  private static void getAllJarContents(String jarPath, List<String> allJarClasses) {
    try (JarFile jf = new JarFile(jarPath)) {
      for (Enumeration<JarEntry> en = jf.entries(); en.hasMoreElements(); ) {
        JarEntry e = en.nextElement();
        String name = e.getName();
        // Check for package or sub-package (you can change the test for *exact* package here)
        if (name.endsWith(".class")) {
          // Strip out ".class" and reformat path to package name
          String javaName = name.substring(0, name.lastIndexOf('.')).replace('/', '.');
          allJarClasses.add(MangleTool.mangleClassSymbolName(javaName));
        }
      }
    } catch (IOException e) {
      e.printStackTrace();
    }
  }

  /***
   * Using the Zip related feature to extract class names.
   * @param jarFile
   * @return
   * @throws IOException
   */
  private static List<String> getClassesInJar(File jarFile) throws IOException {
    List<String> classNames = new ArrayList<String>();
    ZipInputStream zip = new ZipInputStream(new FileInputStream(jarFile));
    for (ZipEntry entry = zip.getNextEntry(); entry != null; entry = zip.getNextEntry()) {
      if (!entry.isDirectory() && entry.getName().endsWith(".class")) {
        // This ZipEntry represents a class. Now, what class does it represent?
        String className = entry.getName().replace('/', '.'); // including ".class"
        classNames.add(className.substring(0, className.length() - ".class".length()));
      }
    }
    return classNames;
  }

  /***
   * Read from the .o.W.list File to get the result of the ir_b2a and file_transformer.py
   * @param objectFileName
   * @param allVTables
   * @param allClassSymbols
   */
  private static void getClassSymbolNamesFromList(String objectFileName, Map<String, List<String>> allVTables, List<String> allClassSymbols) {
    List<String> lst = Utils.readListFromFile(objectFileName);
    // Should execute ir_b2a to generate the result.
    if(new File(objectFileName).exists()) {
      // read-in the results.
      Utils.readPrefixedList(new File(objectFileName),
              allVTables, allClassSymbols);
    }
    return;
  }
}
