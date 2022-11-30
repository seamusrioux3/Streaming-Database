USE streamingdatabase;

DROP FUNCTION IF EXISTS findUser;

DELIMITER $$
CREATE FUNCTION findUser(email_p VARCHAR(128), phone_p VARCHAR(10)) 
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN 
	DECLARE uid_found INT;
    DECLARE uid_not_found INT;
	DECLARE user_cursor CURSOR FOR SELECT userId FROM users WHERE email = email_p AND phone = phone_p;
	DECLARE CONTINUE HANDLER FOR NOT FOUND
		SET uid_not_found = TRUE;

	SET uid_not_found = FALSE;
	OPEN user_cursor;
	
	FETCH user_cursor INTO uid_found;
	
	CLOSE user_cursor;
    
	RETURN uid_found;
END $$

DELIMITER ;
; 

DROP FUNCTION IF EXISTS countSongsInPlaylist;

DELIMITER $$
CREATE FUNCTION countSongsInPlaylist(playlist_id INT) 
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN 
	DECLARE song_count INT;
    SELECT count(*) INTO song_count FROM playlistsong WHERE playlistId = playlist_id;
	RETURN song_count;
END $$

DELIMITER ;
SELECT countSongsInPlaylist(1) as a;
; 